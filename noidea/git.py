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


def get_git_root() -> str:
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
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip()


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        text=True,
        capture_output=True,
        check=False,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def get_diff() -> DiffResult:
    try:
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

    return ".git/hooks"


def install_hook() -> HookResult:
    hooks_dir = get_hooks_dir()

    if hooks_dir is None:
        return HookResult(success=False, error="Not inside a git repository")

    hook_path = os.path.join(hooks_dir, "prepare-commit-msg")

    try:
        os.makedirs(hooks_dir, exist_ok=True)

        if os.path.exists(hook_path):
            if os.path.exists(hook_path + ".bak"):
                print("There is already a backup of the hook present.")
                print("skipping backup creation")
            else:
                os.rename(hook_path, hook_path + ".bak")

        with open(hook_path, "w") as f:
            f.write('#!/bin/bash\nnoidea suggest --file "$1"\n')

        os.chmod(hook_path, mode=0o755)

    except Exception as e:
        return HookResult(success=False, error=str(e))

    return HookResult(success=True)
