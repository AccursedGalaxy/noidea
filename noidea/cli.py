import subprocess
import sys
from typing import Optional

import typer

from noidea import __version__
from noidea.config import load_config
from noidea.git import get_diff, install_hook
from noidea.provider import get_commit_message

app = typer.Typer(help="AI-powered git commit messages.")


def version_callback(value: bool):
    if value:
        typer.echo(f"noidea {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    pass


@app.command()
def init():
    """Install the git commit-msg hook into the current git repository"""
    install_hook()
    print("Git hook installed successfully.")


@app.command()
def suggest(
    file: str = typer.Option(
        None, "--file", "-F", help="Write output to a file instead of stdout"
    )
):
    """Suggest a commit message for the current staged diff"""
    diff = get_diff()
    if diff == "none":
        print("No Changes have been detected")
        return
    config = load_config()
    commit_message = get_commit_message(
        diff,
        config["llm"]["system_prompt"],
        config["llm"]["model"],
        config["llm"]["max_tokens"],
    )
    if file:
        with open(file, "w") as f:
            f.write(commit_message)
    else:
        print(commit_message)


@app.command()
def update():
    """Update noidea to the latest version."""
    try:
        result = subprocess.run(["pipx", "upgrade", "noidea"], check=True)
    except FileNotFoundError:
        # pipx not available, fall back to pip
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "noidea"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        typer.echo(f"Update failed: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
