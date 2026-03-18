import subprocess
import sys
from typing import Optional

import keyring
import typer
from rich.console import Console

from noidea import __version__
from noidea.config import (
    Provider,
    initialize,
    list_keys,
    load_config,
    remove_key,
    save_key,
)
from noidea.git import get_diff, install_hook
from noidea.provider import get_commit_message

app = typer.Typer(help="AI-powered git commit messages.")
keys_app = typer.Typer(help="Manage your API keys via keyring storage.")
app.add_typer(keys_app, name="keys")

console = Console(stderr=True)


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
    initialize()


###
### Feature Commands
###


@app.command()
def init():
    """Install the git commit-msg hook into the current git repository"""
    result = install_hook()
    if result.success:
        print("Git hook installed successfully.")
    else:
        print(f"Something went wrong: {result.error}")


@app.command()
def suggest(
    file: str = typer.Option(
        None, "--file", "-F", help="Write output to a file instead of stdout"
    )
):
    """Suggest a commit message for the current staged diff"""
    try:
        diff = get_diff()
        if not diff.has_changes:
            print("No Changes have been staged")
            return
        config = load_config()
        with console.status("[cyan]Generating commit message...", spinner="dots"):
            commit_message = get_commit_message(
                diff.diff,
                config["llm"]["system_prompt"],
                config["llm"]["model"],
                config["llm"]["max_tokens"],
            )
        if file:
            with open(file, "w") as f:
                f.write(commit_message)
            console.print("[bold green]Commit message ready.[/bold green]")
        else:
            print(commit_message)
    except Exception as e:
        print(f"Something went wrong: {e}")


###
### API Key Commands
###


@keys_app.command()
def show():
    """Show all saved API keys"""
    try:
        keys = list_keys()
        if keys == []:
            print("You have no keys saved yet")
        for key in keys:
            print(key)
    except Exception as e:
        print(f"Something went wrong: {e}")


@keys_app.command()
def add(provider: Provider = typer.Argument(default=Provider.ANTHROPIC)):
    """Add a API key to keyring storage"""
    try:
        key = typer.prompt("Enter your key:", hide_input=True)
        keyring.set_password(
            service_name="noidea", username=provider.value, password=key
        )
        if save_key(provider.value):
            print("API key saved successfully!")
        else:
            print("you alrady have a api saved for this provider")
    except Exception as e:
        print(f"Something went wrong: {e}")


@keys_app.command()
def remove(provider: Provider = typer.Argument(...)):
    """Remove a API key from keyring storage"""
    try:
        keyring.delete_password(service_name="noidea", username=provider.value)
        if remove_key(provider.value):
            print("Key deleted successfully!")
        else:
            print("Unable to delete key. Keys file or key don't exist.")
    except Exception as e:
        print(f"Something went wrong: {e}")


###
### Management Commands
###


@app.command()
def test():
    """Send a dummy message to the API to test."""
    try:
        test_msg = get_commit_message(
            diff="say hi",
            system_prompt="test",
            model="claude-sonnet-4-6",
            max_tokens=1024,
        )
        print("Test successful!")
        print(f"API response: {test_msg}")
    except Exception as e:
        print(f"Something went wrong: {e}")


@app.command()
def update():
    """Update noidea to the latest version."""
    try:
        subprocess.run(["pipx", "upgrade", "noidea"], check=True)
    except FileNotFoundError:
        # pipx not available, fall back to pip
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "noidea"],
                check=True,
            )
        except Exception as e:
            print(f"Something went wrong during the update: {e}")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Update failed: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
