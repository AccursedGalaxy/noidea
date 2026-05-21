import dataclasses

import typer
from rich.console import Console

from noidea.config import LlmConfig, load_config
from noidea.git import get_branch_name, get_diff, get_staged_files
from noidea.provider import ErrorKind, ProviderError, complete

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


def _build_user_content(diff: str, branch: str, staged_files: list[str]) -> str:
    """Assemble the user message from git context. The only commit-specific logic, kept pure."""
    assert isinstance(diff, str), "diff must be a string"
    assert isinstance(staged_files, list), "staged_files must be a list"
    context_parts = []
    if branch:
        context_parts.append(f"Branch: {branch}")
    if staged_files:
        context_parts.append("Staged files:\n" + "\n".join(f"- {f}" for f in staged_files))
    user_content = ""
    if context_parts:
        user_content = "\n".join(context_parts) + "\n\nDiff:\n"
    user_content += diff
    assert isinstance(user_content, str) and user_content, "user_content must be non-empty"
    return user_content


def _generate_message(diff, cfg: LlmConfig, model, branch, staged_files) -> str | None:
    """Call the API and return the commit message, or None on a handled provider error."""
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    assert isinstance(model, str) and model, "model must be a non-empty string"
    user_content = _build_user_content(diff, branch, staged_files)
    # complete() raises one ProviderError; wording per kind stays local to this command.
    try:
        with console.status("[grey]Thinking of something clever...", spinner="dots"):
            return complete(
                cfg.system_prompt,
                user_content,
                model,
                cfg.max_tokens,
                cfg.temperature,
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
    # Character count, not tokens: real tokenization needs the API, but char
    # count is cheap and sufficient for choosing between small and large model.
    context_length_chars = len(cfg.system_prompt) + len(diff.diff)

    selected_model = cfg.select_model(context_length_chars)

    commit_message = _generate_message(diff.diff, cfg, selected_model, branch, staged_files)
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
