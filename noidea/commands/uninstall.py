"""Remove noidea from a repository, and with --purge from the whole machine (issue #10)."""

import os
import shutil

import typer
from rich.console import Console

from noidea.config import CONFIG_DIR
from noidea.dogfood import remove_repo_state
from noidea.git import UninstallResult, get_git_root, uninstall_hooks
from noidea.key_store import KeyStoreError, key_store

console = Console()


def _report_hooks(result: UninstallResult) -> None:
    """Say what happened to each hook, including any user hook deliberately left in place."""
    assert result.success, "only a successful uninstall has hooks to report"
    for name in result.removed:
        console.print(f"Removed {name} hook.")
    for name in result.restored:
        console.print(f"Restored your original {name} from {name}.bak.")
    # A hook noidea did not write (or one the user edited) is theirs to delete, never ours.
    for name in result.skipped:
        console.print(
            f"[yellow]Left {name} in place:[/yellow] noidea did not write it (or it was edited)."
        )
    if not (result.removed or result.skipped):
        console.print("No noidea hooks found in this repository.")


def _purge() -> None:
    """Remove every stored API key, then the global config directory."""
    try:
        for provider in key_store.list():
            key_store.remove(provider)
            console.print(f"Removed API key: {provider}")
    except KeyStoreError as error:
        console.print(f"[red]Could not remove API keys:[/red] {error}")
    if os.path.isdir(CONFIG_DIR):
        shutil.rmtree(CONFIG_DIR)
        console.print(f"Deleted config directory: {CONFIG_DIR}", soft_wrap=True)
    assert not os.path.exists(CONFIG_DIR), "purge must leave no config directory behind"


def uninstall(
    purge: bool = typer.Option(
        False,
        "--purge",
        help="Also delete stored API keys and ~/.noidea (config, dogfood records).",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the --purge confirmation."
    ),
):
    """Remove noidea's git hooks from this repo, restoring any hook it replaced."""
    if purge and not yes:
        # Purge deletes secrets and records that cannot be recovered, so it asks first.
        typer.confirm(
            f"Delete all noidea API keys and {CONFIG_DIR}?", abort=True, err=True
        )
    result = uninstall_hooks()
    if result.success:
        _report_hooks(result)
        repo_root = get_git_root()
        if repo_root and remove_repo_state(repo_root):
            console.print("Removed noidea's per-repo state (.git/noidea).")
    elif not purge:
        console.print(f"[red]Couldn't uninstall:[/red] {result.error}")
        raise typer.Exit(code=1)
    else:
        # Purge is machine-wide, so it still cleans up global state outside a repository.
        console.print(f"[dim]Skipping hooks: {result.error}.[/dim]")
    if purge:
        _purge()
