import os
import subprocess


def get_diff():
    diff = subprocess.run(["git", "diff", "--staged"], capture_output=True, text=True)
    if not diff.stdout:
        return "none"
    return diff.stdout


def get_hooks_dir() -> str:
    hooks_dir = subprocess.run(
        ["git", "config", "core.hooksPath"], capture_output=True, text=True
    )
    if not hooks_dir.stdout:
        return ".git/hooks"

    return hooks_dir.stdout.strip()


def install_hook():
    hooks_dir = get_hooks_dir()
    hook_path = os.path.join(hooks_dir, "prepare-commit-msg")

    if os.path.exists(hook_path):
        os.rename(hook_path, hook_path + ".bak")

    with open(hook_path, "w") as f:
        f.write('#!/bin/bash\nnoidea suggest --file "$1"\n')

    os.chmod(hook_path, mode=0o755)
