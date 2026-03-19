import typer

from noidea.git import install_hook


def init():
    """Install the git commit-msg hook into the current git repository"""
    result = install_hook()
    if result.success:
        print("Git hook installed successfully.")
    else:
        print(f"Something went wrong: {result.error}")
