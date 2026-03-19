import subprocess
import sys

import typer


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
