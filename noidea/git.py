import os
import subprocess


def get_diff():
    try:
        diff = subprocess.run(
            ["git", "diff", "--staged"], capture_output=True, text=True, check=True
        )
        if not diff.stdout:
            return "none"
        return diff.stdout
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return "none"
    except FileNotFoundError as e:
        print(e)
        return "none"


def get_hooks_dir() -> str:
    try:
        hooks_dir = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True,
            text=True,
            check=True,
        )
        if not hooks_dir.stdout:
            return ".git/hooks"
        return hooks_dir.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return ".git/hooks"
    except FileNotFoundError as e:
        print(e)
        return ".git/hooks"


def install_hook():
    hooks_dir = get_hooks_dir()
    hook_path = os.path.join(hooks_dir, "prepare-commit-msg")

    try:
        if not os.path.exists(hooks_dir):
            os.mkdir(hooks_dir)

        if os.path.exists(hook_path):
            os.rename(hook_path, hook_path + ".bak")

        with open(hook_path, "w") as f:
            f.write('#!/bin/bash\nnoidea suggest --file "$1"\n')
        os.chmod(hook_path, mode=0o755)
    except Exception as e:
        print(e)
