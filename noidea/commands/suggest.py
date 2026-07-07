import dataclasses

import typer
from rich.console import Console

from noidea.agent_backend import generate_with_agent
from noidea.config import LlmConfig, load_config
from noidea.dogfood import (
    clear_seeded,
    find_fresh_proposal,
    mark_seeded,
    new_run_id,
    record_proposal,
    run_file_for,
)
from noidea.git import (
    get_branch_name,
    get_diff,
    get_git_root,
    get_recent_commits,
    get_staged_files,
)
from noidea.provider import (
    ErrorKind,
    ProviderError,
    complete,
    context_window_tokens,
)
from noidea.style import SAMPLE_SIZE, analyze_commits, render_profile

console = Console(stderr=True)

# Per-command wording for each failure kind. Kept here (not in provider) so the message suits
# the suggest context; keyed on ErrorKind so adding a kind forces a deliberate update here.
SUGGEST_WORDING = {
    ErrorKind.AUTH: lambda e: f"Authentication failed. Check your API key: {e.message}",
    ErrorKind.RATE_LIMIT: lambda e: f"Rate limited. Try again shortly: {e.message}",
    ErrorKind.CONNECTION: lambda e: f"Could not connect to the API: {e.message}",
    ErrorKind.STATUS: lambda e: f"API error ({e.status_code}): {e.message}",
}
assert set(SUGGEST_WORDING) == set(ErrorKind), (
    "SUGGEST_WORDING must cover every ErrorKind"
)


# Fraction of a model's context window we allow the diff to fill, leaving headroom for the system
# prompt, the branch/file scaffolding, and the model's own output. 10% headroom on a 1M window is
# ~100k tokens — far more than we ever need.
_DIFF_CONTEXT_SAFETY_FRACTION = 0.9
# Characters per token assumed when converting a token window to a character budget. Measured ~3.1
# on dense JSON diffs (the worst case); using a low ratio keeps the char budget conservative, so
# denser-than-prose content still fits rather than overflowing.
_CHARS_PER_TOKEN = 3.0


def _diff_budget_chars(model: str, cfg: LlmConfig) -> int:
    """The maximum diff characters to send to `model`, from its context window and any config cap.

    Auto by default: the selected model's own window sets the bound, so a 1M-token model gets a
    large budget and a 128k one a small budget (which also prevents a mis-routed diff from
    overflowing the smaller model). A positive cfg.diff_chars_max caps below that for cost control.
    """
    assert isinstance(model, str) and model, "model must be a non-empty string"
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    window_tokens = context_window_tokens(model)
    auto_budget = int(window_tokens * _DIFF_CONTEXT_SAFETY_FRACTION * _CHARS_PER_TOKEN)
    # A positive config value is a hard ceiling; 0 means "auto", so the window-derived budget wins.
    if cfg.diff_chars_max > 0:
        auto_budget = min(auto_budget, cfg.diff_chars_max)
    assert auto_budget > 0, "diff budget must be positive"
    return auto_budget


def _cap_diff(diff: str, chars_max: int) -> str:
    """Bound the diff sent to the model so an enormous staged change can't blow the context window.

    A commit of generated artifacts or a vendored tree can run to hundreds of thousands of tokens,
    exceeding every provider's context window and failing the request outright. The full list of
    changed files travels separately in the prompt (staged_files), so a truncated diff still names
    every file; only the hunk bodies past the cap are dropped. Returns diff unchanged when it fits.
    """
    assert isinstance(diff, str), "diff must be a string"
    assert isinstance(chars_max, int) and chars_max > 0, (
        "chars_max must be a positive int"
    )
    if len(diff) <= chars_max:
        return diff
    dropped_chars = len(diff) - chars_max
    notice = (
        f"\n\n[diff truncated: {dropped_chars} of {len(diff)} characters omitted to fit the"
        " model context window; the full changed-file list is listed above]"
    )
    result = diff[:chars_max] + notice
    assert result.startswith(diff[:chars_max]), (
        "capped diff must retain the head up to the cap"
    )
    return result


def _build_user_content(
    diff: str, branch: str, staged_files: list[str], profile_text: str = ""
) -> str:
    """Assemble the user message from git context. The only commit-specific logic, kept pure."""
    assert isinstance(diff, str), "diff must be a string"
    assert isinstance(staged_files, list), "staged_files must be a list"
    assert isinstance(profile_text, str), "profile_text must be a string"
    context_parts = []
    if branch:
        context_parts.append(f"Branch: {branch}")
    if staged_files:
        context_parts.append(
            "Staged files:\n" + "\n".join(f"- {f}" for f in staged_files)
        )
    # The learned conventions sit with the other context, before the diff.
    if profile_text:
        context_parts.append(profile_text)
    user_content = ""
    if context_parts:
        user_content = "\n".join(context_parts) + "\n\nDiff:\n"
    user_content += diff
    assert isinstance(user_content, str) and user_content, (
        "user_content must be non-empty"
    )
    return user_content


def _learn_style(cfg: LlmConfig) -> str:
    """Distil the repo's commit conventions into a prompt block, or "" if off/insufficient.

    Best-effort: get_recent_commits never raises and analyze_commits returns None below the
    minimum sample, so this degrades to "" (today's behavior) rather than blocking a commit.
    """
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    if not cfg.learn_commit_style:
        return ""
    profile = analyze_commits(get_recent_commits(SAMPLE_SIZE))
    profile_text = render_profile(profile) if profile is not None else ""
    assert isinstance(profile_text, str), "profile_text must be a string"
    return profile_text


def _print_routing_notice(cfg: LlmConfig, selected_model: str) -> None:
    """Surface the cost-aware routing decision so its value is felt, not buried in config.

    Printed to stderr (the message itself goes to stdout / the hook file), so it never
    pollutes what the hook consumes. The caller skips it when --model forces a single
    model, since then there is no routing decision to report.
    """
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    assert isinstance(selected_model, str) and selected_model, (
        "selected_model must be non-empty"
    )
    if selected_model == cfg.small_model:
        console.print(f"[dim]Small diff → {selected_model} · fast & cheap[/dim]")
    else:
        console.print(
            f"[dim]Large change → escalating to {selected_model} · the strong model[/dim]"
        )


def _generate_message(
    diff, cfg: LlmConfig, model, branch, staged_files, profile_text
) -> str | None:
    """Call the API and return the commit message, or None on a handled provider error."""
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    assert isinstance(model, str) and model, "model must be a non-empty string"
    user_content = _build_user_content(diff, branch, staged_files, profile_text)
    # complete() raises one ProviderError; wording per kind stays local to this command.
    try:
        with console.status("[grey]Thinking of something clever...", spinner="dots"):
            return complete(
                cfg.system_prompt,
                user_content,
                model,
                cfg.max_tokens,
                cfg.temperature,
                provider=cfg.provider,
                base_url=cfg.base_url,
            )
    except ProviderError as error:
        print(SUGGEST_WORDING[error.kind](error))
        return None


def _emit_message(message: str, file: str) -> None:
    """Write the message to the commit-msg file, or print it to stdout when no file is given."""
    assert isinstance(message, str) and message, "message must be a non-empty string"
    if not file:
        print(message)
        return
    try:
        with open(file, "w") as handle:
            handle.write(message)
    except OSError as error:
        print(f"Could not write to {file}: {error}")
        return
    console.print("[bold green]Done. You're welcome.[/bold green]")


def _seed_pending(
    repo_root: str, file: str, branch: str, staged_files: list[str], cfg: LlmConfig
) -> bool:
    """Seed an already-queued agent proposal into the commit buffer (no model call); True if one matched.

    Preferred over regenerating: an earlier explicit `noidea suggest --agent` already paid for
    this message. If a fresh proposal matches the staged change, write it verbatim and record the
    seed pointer so post-commit reconciles it. The caller clears the pointer first (see suggest).
    """
    assert isinstance(repo_root, str) and repo_root, "repo_root must be non-empty"
    assert isinstance(file, str) and file, "file must be a non-empty path"
    proposal = find_fresh_proposal(
        repo_root, staged_files, branch, cfg.agent_proposal_ttl_seconds
    )
    if proposal is None:
        return False
    try:
        with open(file, "w") as handle:
            handle.write(proposal.proposed_message)
    except OSError as error:
        console.print(f"[dim]could not seed agent message into {file}: {error}[/dim]")
        return False
    mark_seeded(repo_root, proposal.run_id)
    console.print(f"[dim]Using queued agent commit message ({proposal.run_id}).[/dim]")
    return True


def _run_agent_backend(
    diff: str, branch: str, staged_files: list[str], repo_root: str, cfg: LlmConfig
) -> tuple[str, str] | None:
    """Generate via the driver-os agent and queue the proposal; returns (message, run_id) or None.

    None means the agent was unavailable or failed, so the caller falls back to the fast path —
    an agent failure must never block a commit. The run_id lets the caller mark the seed pointer
    when it writes the message straight into the commit buffer (the inline-hook path).
    """
    assert isinstance(diff, str) and diff.strip(), "diff must be a non-empty string"
    run_id = new_run_id()
    run_file = run_file_for(run_id)
    with console.status("[grey]Agent investigating the repo...", spinner="dots"):
        message = generate_with_agent(
            repo_root, diff, branch, staged_files, run_file, cfg
        )
    if message is None:
        return None
    record_proposal(
        repo_root,
        run_id,
        branch,
        staged_files,
        message,
        run_file,
        cfg.agent_proposal_ttl_seconds,
    )
    return message, run_id


def suggest(
    file: str = typer.Option(
        None, "--file", "-F", help="Write output to a file instead of stdout"
    ),
    model: str = typer.Option(
        None, "--model", "-M", help="Run suggestion with a different model"
    ),
    agent: bool = typer.Option(
        None,
        "--agent/--no-agent",
        help="Use the driver-os agent backend (richer, slower). Defaults to llm.use_agent.",
    ),
):
    """Let AI do the thinking. Generates a commit message from your staged changes."""
    diff = get_diff()
    if not diff.has_changes:
        print(
            "Nothing staged yet. Stage some changes first — we can't read your mind (yet)."
        )
        return

    # TigerStyle: validate external data before sending to API.
    if not diff.diff.strip():
        print("Staged changes produced an empty diff. Nothing to do.")
        return

    cfg = load_config()
    # CLI flag config override: both models become the requested one, so select_model
    # returns it regardless of context size.
    if model:
        cfg = dataclasses.replace(cfg, small_model=model, large_model=model)
    branch = get_branch_name()
    staged_files = get_staged_files()
    repo_root = get_git_root()
    # The flag (--agent/--no-agent) overrides the configured default; absent, the config decides.
    use_agent = agent if agent is not None else cfg.use_agent

    # Each commit attempt starts by clearing the seed pointer so a fast-path commit is never
    # mis-reconciled as an agent one. The hook is the only caller that passes --file.
    if file and repo_root:
        clear_seeded(repo_root)

    # Prefer an already-queued proposal from an earlier explicit `--agent` run: it is paid for,
    # so seed it rather than regenerate. Hook only (--file), and skipped when a flag forces a
    # fresh decision (--agent regenerates; --no-agent opts out entirely).
    if (
        file
        and agent is None
        and repo_root
        and _seed_pending(repo_root, file, branch, staged_files, cfg)
    ):
        return

    # Agent generation: explicit --agent, or the use_agent default. Runs inline even on the
    # commit hook (the chosen "agent by default" behavior). Falls through to the fast path on any
    # agent failure, so an unavailable backend never blocks a commit. Bound the seed diff to the
    # agent model's own window so a huge staged change can't overflow it.
    if use_agent and repo_root:
        agent_diff = _cap_diff(diff.diff, _diff_budget_chars(cfg.agent_model, cfg))
        result = _run_agent_backend(agent_diff, branch, staged_files, repo_root, cfg)
        if result is not None:
            message, run_id = result
            if file:
                mark_seeded(
                    repo_root, run_id
                )  # so post-commit reconciles this inline run.
            _emit_message(message, file)
            return

    # Fast single-shot path (the default when the agent is off or unavailable).
    profile_text = _learn_style(cfg)
    # Character count, not tokens: real tokenization needs the API, but char
    # count is cheap and sufficient for choosing between small and large model.
    context_length_chars = len(cfg.system_prompt) + len(diff.diff)
    selected_model = cfg.select_model(context_length_chars)
    # Show the routing decision, except when --model or the agent meant no decision was made.
    if not model and not use_agent:
        _print_routing_notice(cfg, selected_model)

    # Bound the diff to the selected model's own window; this also protects the small model when a
    # borderline-size diff routes to it, since the cap follows the model that will receive it.
    capped_diff = _cap_diff(diff.diff, _diff_budget_chars(selected_model, cfg))
    commit_message = _generate_message(
        capped_diff, cfg, selected_model, branch, staged_files, profile_text
    )
    if commit_message is None:
        return
    _emit_message(commit_message, file)
