import subprocess
import sys

import typer


def update():
    """Get the latest noidea — now with even less idea required."""
    try:
        subprocess.run(["pipx", "upgrade", "noidea"], check=True)
    except FileNotFoundError:
        # pipx not available, fall back to pip
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "noidea"],
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Update failed: {e}")
    except subprocess.CalledProcessError as e:
        typer.echo(f"Update failed: {e}", err=True)
        raise typer.Exit(1)
