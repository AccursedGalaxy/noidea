import dataclasses

import anthropic
import typer
from rich.console import Console

from noidea.config import LlmConfig, load_config
from noidea.git import get_branch_name, get_diff, get_staged_files
from noidea.provider import get_commit_message

console = Console(stderr=True)


def _generate_message(diff, cfg: LlmConfig, model, branch, staged_files) -> str | None:
    """Call the API and return the commit message, or None on handled error."""
    assert isinstance(cfg, LlmConfig), "cfg must be an LlmConfig"
    try:
        with console.status("[grey]Thinking of something clever...", spinner="dots"):
            return get_commit_message(
                diff,
                cfg.system_prompt,
                model,
                cfg.max_tokens,
                branch=branch,
                staged_files=staged_files,
                temperature=cfg.temperature,
            )
    # Errors handled here (not in provider.py) because each caller needs
    # different user-facing messages and recovery behavior.
    except KeyboardInterrupt:
        raise
    except anthropic.AuthenticationError as error:
        print(f"Authentication failed. Check your API key: {error.message}")
    except anthropic.RateLimitError as error:
        print(f"Rate limited. Try again shortly: {error.message}")
    except anthropic.APIConnectionError as error:
        print(f"Could not connect to the API: {error}")
    except anthropic.APIStatusError as error:
        print(f"API error ({error.status_code}): {error.message}")
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
