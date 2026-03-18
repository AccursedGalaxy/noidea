import subprocess
import sys
from typing import Optional

import keyring
import typer

from noidea import __version__
from noidea.config import list_keys, load_config, remove_key, save_key
from noidea.git import get_diff, install_hook
from noidea.provider import get_commit_message

app = typer.Typer(help="AI-powered git commit messages.")
keys_app = typer.Typer(help="Manage your API keys via keyring storage.")
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
    try:
        install_hook()
        print("Git hook installed successfully.")
    except Exception as e:
        print(f"Something went wrong: {e}")


@app.command()
def suggest(
    file: str = typer.Option(
        None, "--file", "-F", help="Write output to a file instead of stdout"
    )
):
    """Suggest a commit message for the current staged diff"""
    try:
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
    except Exception as e:
        print(f"Something went wrong: {e}")


###
### API Key Commands
###


@keys_app.command()
def list():
    """List all saved API keys"""
    try:
        list_keys()
    except Exception as e:
        print(f"Something went wrong: {e}")


@keys_app.command()
def add():
    """Add a API key to keyring storage"""
    try:
        key = typer.prompt("Enter your key:", hide_input=True)
        keyring.set_password(service_name="noidea", username="Anthropic", password=key)
        save_key("Anthropic")
        print("API key saved successfully!")
    except Exception as e:
        print(f"Something went wrong: {e}")


@keys_app.command()
def remove():
    """Remove a API key from keyring storage"""
    try:
        name = typer.prompt("Which key do you want to delete?")
        keyring.delete_password(service_name="noidea", username=name)
        remove_key(name)
        print("Key deleted successfully!")
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
