import typer

from noidea.config import Provider
from noidea.key_store import KeyStoreError, key_store

keys_app = typer.Typer(help="Manage your API keys. The one secret you actually need to keep.")


@keys_app.command()
def show():
    """Show your saved API keys."""
    try:
        keys = key_store.list()
        if not keys:
            print("No keys found. Run 'noidea keys add' to get started.")
        for key in keys:
            print(key)
    except KeyStoreError as e:
        print(f"Couldn't read keys: {e}")


@keys_app.command()
def add(provider: Provider = typer.Argument(default=Provider.ANTHROPIC)):
    """Stash an API key in your keyring. Ollama is local and needs no key — skip this for it."""
    try:
        key = typer.prompt("Enter your key:", hide_input=True)
        if key_store.add(provider.value, key):
            print("Key saved. You're ready to have no idea what to commit.")
        else:
            print("You already have a key saved for this provider.")
    except KeyStoreError as e:
        print(f"Couldn't save the key: {e}")


@keys_app.command()
def remove(provider: Provider = typer.Argument(...)):
    """Remove an API key from your keyring."""
    try:
        if key_store.remove(provider.value):
            print("Key removed. Gone, like your commit message inspiration.")
        else:
            print("Key not found. Nothing to remove.")
    except KeyStoreError as e:
        print(f"Couldn't remove the key: {e}")
