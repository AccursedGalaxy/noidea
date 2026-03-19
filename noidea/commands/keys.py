import keyring
import typer

from noidea.config import Provider, list_keys, remove_key, save_key

keys_app = typer.Typer(help="Manage your API keys via keyring storage.")


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
            print("you already have a api saved for this provider")
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
