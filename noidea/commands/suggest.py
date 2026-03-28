import anthropic
import typer
from rich.console import Console

from noidea.config import deep_merge, load_config
from noidea.git import get_branch_name, get_diff, get_staged_files
from noidea.provider import get_commit_message

console = Console(stderr=True)


def suggest(
    file: str = typer.Option(
        None, "--file", "-F", help="Write output to a file instead of stdout"
    ),
    model: str = typer.Option(
        None, "--model", "-M", help="Run suggestion with a different model"
    ),
):
    """Let AI do the thinking. Generates a commit message from your staged changes."""
    diff = get_diff()
    if not diff.has_changes:
        print(
            "Nothing staged yet. Stage some changes first"
            " — we can't read your mind (yet)."
        )
        return

    # TigerStyle: validate external data before sending to API.
    if not diff.diff.strip():
        print("Staged changes produced an empty diff. Nothing to do.")
        return

    config = load_config()

    # CLI flag config override.
    if model:
        config = deep_merge(
            config, {"llm": {"small_model": model, "large_model": model}}
        )

    branch = get_branch_name()
    staged_files = get_staged_files()
    # Character count, not tokens: real tokenization needs the API, but char
    # count is cheap and sufficient for choosing between small and large model.
    context_length_chars = len(config["llm"]["system_prompt"]) + len(diff.diff)

    try:
        with console.status("[grey]Thinking of something clever...", spinner="dots"):
            selected_model = (
                config["llm"]["large_model"]
                if context_length_chars >= config["llm"]["context_limit"]
                else config["llm"]["small_model"]
            )
            commit_message = get_commit_message(
                diff.diff,
                config["llm"]["system_prompt"],
                selected_model,
                config["llm"]["max_tokens"],
                branch=branch,
                staged_files=staged_files,
                temperature=config["llm"]["temperature"],
            )
    # Errors handled here (not in provider.py) because each caller needs
    # different user-facing messages and recovery behavior.
    except KeyboardInterrupt:
        raise
    except anthropic.AuthenticationError as error:
        print(f"Authentication failed. Check your API key: {error.message}")
        return
    except anthropic.RateLimitError as error:
        print(f"Rate limited. Try again shortly: {error.message}")
        return
    except anthropic.APIConnectionError as error:
        print(f"Could not connect to the API: {error}")
        return
    except anthropic.APIStatusError as error:
        print(f"API error ({error.status_code}): {error.message}")
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
