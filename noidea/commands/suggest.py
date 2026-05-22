import dataclasses

import typer
from rich.console import Console

from noidea.config import LlmConfig, load_config
from noidea.git import get_branch_name, get_diff, get_recent_commits, get_staged_files
from noidea.provider import ErrorKind, ProviderError, complete
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
assert set(SUGGEST_WORDING) == set(ErrorKind), "SUGGEST_WORDING must cover every ErrorKind"


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
        context_parts.append("Staged files:\n" + "\n".join(f"- {f}" for f in staged_files))
    # The learned conventions sit with the other context, before the diff.
    if profile_text:
        context_parts.append(profile_text)
    user_content = ""
    if context_parts:
        user_content = "\n".join(context_parts) + "\n\nDiff:\n"
    user_content += diff
    assert isinstance(user_content, str) and user_content, "user_content must be non-empty"
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
    assert isinstance(selected_model, str) and selected_model, "selected_model must be non-empty"
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


def suggest(
    file: str = typer.Option(None, "--file", "-F", help="Write output to a file instead of stdout"),
    model: str = typer.Option(None, "--model", "-M", help="Run suggestion with a different model"),
):
    """Let AI do the thinking. Generates a commit message from your staged changes."""
    diff = get_diff()
    if not diff.has_changes:
        print("Nothing staged yet. Stage some changes first" " — we can't read your mind (yet).")
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
    profile_text = _learn_style(cfg)
    # Character count, not tokens: real tokenization needs the API, but char
    # count is cheap and sufficient for choosing between small and large model.
    context_length_chars = len(cfg.system_prompt) + len(diff.diff)

    selected_model = cfg.select_model(context_length_chars)
    # Show the routing decision, except when --model forced a single model (no decision made).
    if not model:
        _print_routing_notice(cfg, selected_model)

    commit_message = _generate_message(
        diff.diff, cfg, selected_model, branch, staged_files, profile_text
    )
    if commit_message is None:
        return

    if file:
        try:
            with open(file, "w") as f:
                f.write(commit_message)
        except OSError as error:
            print(f"Could not write to {file}: {error}")
            return
        console.print("[bold green]Done. You're welcome.[/bold green]")
    else:
        print(commit_message)
