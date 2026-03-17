import subprocess
import sys
from os import name
from typing import Optional

import keyring
import typer

from noidea import __version__
from noidea.config import list_keys, load_config, remove_key, save_key
from noidea.git import get_diff, install_hook
from noidea.provider import get_commit_message

app = typer.Typer(help="AI-powered git commit messages.")
keys_app = typer.Typer(help="Manage API Keys.")
app.add_typer(keys_app, name="keys")


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


###
### Feature Commands
###


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


###
### API Key Commands
###


@keys_app.command()
def list():
    """List all saved API keys"""
    list_keys()


@keys_app.command()
def add():
    """Add a API key to keyring storage"""
    key = typer.prompt("Enter your key:", hide_input=True)
    if key:
        keyring.set_password(service_name="noidea", username="Anthropic", password=key)
        save_key("Anthropic")
        print("Api key saved successfully!")
    else:
        print("Something went wrong")


@keys_app.command()
def remove():
    """Remove a API key from keyring storage"""
    name = typer.prompt("Which key do you want to delete?")
    if name:
        keyring.delete_password(service_name="noidea", username=name)
        remove_key(name)
        print("Key deleted successfully!")
    else:
        print("something went wrong")


###
### Management Commands
###


@app.command()
def test():
    """Send a dummy message to the API to test."""
    test_msg = get_commit_message(
        diff="say hi", system_prompt="test", model="claude-sonnet-4-6", max_tokens=1024
    )
    if test_msg:
        print("Test successfull!")
        print(test_msg)
    else:
        print("sad face... something went wrong")


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
