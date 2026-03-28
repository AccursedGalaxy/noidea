"""Git subprocess wrappers that return structured dataclasses instead of raw output."""

import os
import subprocess
from dataclasses import dataclass


@dataclass
class DiffResult:
    has_changes: bool
    diff: str = ""
    error: str = ""


@dataclass
class HookResult:
    success: bool
    error: str = ""


HOOK_NAME = "prepare-commit-msg"
HOOK_BACKUP_SUFFIX = ".bak"
HOOK_SCRIPT = '#!/bin/bash\nnoidea suggest --file "$1"\n'

# TigerStyle: compile-time-style constant assertion.
if not HOOK_SCRIPT.strip():
    raise RuntimeError("HOOK_SCRIPT must not be empty")


def get_git_root() -> str:
    # check=False: best-effort query that degrades gracefully when git is absent.
    git_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    return git_root.stdout.strip()


def is_git_repo() -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True
        ).returncode
        == 0
    )


def get_branch_name() -> str:
    # check=False: caller tolerates empty results when outside a repo.
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip()


def get_staged_files() -> list[str]:
    # check=False: returns empty list if nothing is staged or git is missing.
    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        text=True,
        capture_output=True,
        check=False,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def get_diff() -> DiffResult:
    try:
        # check=True: staged diff is required for the core feature, so failure is an error.
        result = subprocess.run(
            ["git", "diff", "--staged"], capture_output=True, text=True, check=True
        )

        if not result.stdout:
            return DiffResult(has_changes=False)
        else:
            return DiffResult(has_changes=True, diff=result.stdout)

    except subprocess.CalledProcessError as e:
        return DiffResult(has_changes=False, error=e.stderr)

    except FileNotFoundError as e:
        return DiffResult(has_changes=False, error=str(e))


def get_hooks_dir() -> str | None:
    if not is_git_repo():
        return None

    result = subprocess.run(
        ["git", "config", "core.hooksPath"], capture_output=True, text=True
    )

    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    # Default location when core.hooksPath is not configured.
    return ".git/hooks"


def install_hook() -> HookResult:
    hooks_dir = get_hooks_dir()

    if hooks_dir is None:
        return HookResult(success=False, error="Not inside a git repository")

    # TigerStyle: validate data from external source (git subprocess).
    if not isinstance(hooks_dir, str) or not hooks_dir.strip():
        return HookResult(success=False, error="hooks_dir is empty or invalid")

    hook_path = os.path.join(hooks_dir, HOOK_NAME)

    try:
        os.makedirs(hooks_dir, exist_ok=True)

        if os.path.exists(hook_path):
            # Preserve the user's original hook, not our previous version.
            if os.path.exists(hook_path + HOOK_BACKUP_SUFFIX):
                print("There is already a backup of the hook present.")
                print("skipping backup creation")
            else:
                os.rename(hook_path, hook_path + HOOK_BACKUP_SUFFIX)

        with open(hook_path, "w") as f:
            f.write(HOOK_SCRIPT)

        os.chmod(hook_path, mode=0o755)

    except OSError as e:
        return HookResult(success=False, error=str(e))

    return HookResult(success=True)
