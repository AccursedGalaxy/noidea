import keyring
import typer

from noidea.config import Provider, list_keys, remove_key, save_key

keys_app = typer.Typer(
    help="Manage your API keys. The one secret you actually need to keep."
)


@keys_app.command()
def show():
    """Show your saved API keys."""
    try:
        keys = list_keys()
        if keys == []:
            print("No keys found. Run 'noidea keys add' to get started.")
        for key in keys:
            print(key)
    except Exception as e:
        print(f"Couldn't read keys: {e}")


@keys_app.command()
def add(provider: Provider = typer.Argument(default=Provider.ANTHROPIC)):
    """Stash an API key in your keyring."""
    try:
        key = typer.prompt("Enter your key:", hide_input=True)
        keyring.set_password(
            service_name="noidea", username=provider.value, password=key
        )
        if save_key(provider.value):
            print("Key saved. You're ready to have no idea what to commit.")
        else:
            print("You already have a key saved for this provider.")
    except Exception as e:
        print(f"Couldn't save the key: {e}")


@keys_app.command()
def remove(provider: Provider = typer.Argument(...)):
    """Remove an API key from your keyring."""
    try:
        keyring.delete_password(service_name="noidea", username=provider.value)
        if remove_key(provider.value):
            print("Key removed. Gone, like your commit message inspiration.")
        else:
            print("Key not found. Nothing to remove.")
    except Exception as e:
        print(f"Couldn't remove the key: {e}")
