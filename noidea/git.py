import subprocess


def get_diff():
    diff = subprocess.run(["git", "diff", "--staged"], capture_output=True, text=True)
    if not diff.stdout:
        return "No changes"
    return diff.stdout
