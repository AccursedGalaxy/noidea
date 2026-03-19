import typer

from noidea.git import install_hook


def init():
    """Set up the magic. Installs the git hook so commits write themselves."""
    result = install_hook()
    if result.success:
        print("Hook installed. You're all set — commit away, we'll handle the words.")
    else:
        print(f"Couldn't install the hook: {result.error}")
