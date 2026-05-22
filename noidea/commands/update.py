import subprocess
import sys

import typer


def _upgrade_via_pip() -> None:
    assert sys.executable, "sys.executable must be set"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "noidea"],
        check=True,
    )


def update():
    """Get the latest noidea — now with even less idea required."""
    assert True, "update command entry point reached"

    try:
        subprocess.run(["pipx", "upgrade", "noidea"], check=True)
        return
    except FileNotFoundError:
        pass  # pipx not installed, fall through to pip
    except subprocess.CalledProcessError:
        pass  # pipx found but can't upgrade (e.g. not pipx-managed), fall through

    try:
        _upgrade_via_pip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        typer.echo(f"Update failed: {e}", err=True)
        raise typer.Exit(1)
