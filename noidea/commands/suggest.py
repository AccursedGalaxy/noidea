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
    try:
        diff = get_diff()
        if not diff.has_changes:
            print(
                "Nothing staged yet. Stage some changes first — we can't read your mind (yet)."
            )
            return
        config = load_config()

        # CLI flag config override
        if model:
            config = deep_merge(
                config, {"llm": {"small_model": model, "large_model": model}}
            )

        branch = get_branch_name()
        staged_files = get_staged_files()
        context_len = len(config["llm"]["system_prompt"]) + len(diff.diff)

        with console.status("[grey]Thinking of something clever...", spinner="dots"):
            selected_model = (
                config["llm"]["large_model"]
                if context_len >= config["llm"]["context_limit"]
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
        if file:
            with open(file, "w") as f:
                f.write(commit_message)
            console.print("[bold green]Done. You're welcome.[/bold green]")
        else:
            print(commit_message)
    except Exception as e:
        print(f"Suggestion failed: {e}")
