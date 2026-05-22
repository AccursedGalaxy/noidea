"""Git subprocess wrappers that return structured dataclasses instead of raw output."""

import os
import re
import subprocess
from dataclasses import dataclass


@dataclass
class Commit:
    """One sampled commit, split into its subject line and the remaining body."""

    subject: str
    body: str = ""


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
    return subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True).returncode == 0


def get_branch_name() -> str:
    # check=False: caller tolerates empty results when outside a repo.
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip()


# git log format separators: US (0x1f) between subject and body, RS (0x1e) between records.
# These bytes never occur in commit text, so they parse unambiguously.
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"


def get_recent_commits(count: int) -> list[Commit]:
    """Return up to ``count`` recent non-merge commits as Commit objects (subject + body).

    Best-effort like the other wrappers: any failure (shallow clone, git missing, parse
    surprise) returns an empty list rather than raising, so the commit hook never breaks.
    """
    assert isinstance(count, int) and count > 0, "count must be a positive integer"
    # check=False + catching FileNotFoundError: a degraded result must fall back to no style
    # profile, never abort a commit. git missing entirely is just another empty result.
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "-n",
                str(count),
                "--no-merges",
                f"--format=%s{_FIELD_SEP}%b{_RECORD_SEP}",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    commits: list[Commit] = []
    for record in result.stdout.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        subject, _, body = record.partition(_FIELD_SEP)
        commits.append(Commit(subject=subject.strip(), body=body.strip()))
    assert isinstance(commits, list), "get_recent_commits must return a list"
    return commits


def get_staged_files() -> list[str]:
    # check=False: returns empty list if nothing is staged or git is missing.
    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        text=True,
        capture_output=True,
        check=False,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def _strip_binary_hunks(diff_text: str) -> str:
    """Remove binary file hunks from a unified diff, keeping a summary line.

    Binary hunks bloat the prompt without adding useful context for commit
    message generation.  We keep the diff header so the AI knows *which*
    binary files changed.
    """
    assert isinstance(diff_text, str), "diff_text must be a string"

    # Split on "diff --git" boundaries, keeping the delimiter.
    parts = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)

    cleaned: list[str] = []
    for part in parts:
        if not part:
            continue
        # Git marks binary content with this sentinel line.
        if "Binary files" in part or "GIT binary patch" in part:
            # Keep only the header line so the AI sees the filename.
            header = part.split("\n", 1)[0]
            cleaned.append(header + "\n[binary file — diff omitted]\n")
        else:
            cleaned.append(part)

    result = "".join(cleaned)
    assert isinstance(result, str), "result must be a string"
    return result


def get_diff() -> DiffResult:
    try:
        # text=False: binary diffs contain non-UTF-8 bytes that crash text mode.
        result = subprocess.run(["git", "diff", "--staged"], capture_output=True, check=True)

        if not result.stdout:
            return DiffResult(has_changes=False)

        # Decode with replace to survive any stray non-UTF-8 bytes.
        diff_text = result.stdout.decode("utf-8", errors="replace")
        diff_text = _strip_binary_hunks(diff_text)

        assert isinstance(diff_text, str), "diff must be a string after processing"
        return DiffResult(has_changes=True, diff=diff_text)

    except subprocess.CalledProcessError as e:
        return DiffResult(has_changes=False, error=e.stderr.decode("utf-8", errors="replace"))

    except FileNotFoundError as e:
        return DiffResult(has_changes=False, error=str(e))


def get_hooks_dir() -> str | None:
    if not is_git_repo():
        return None

    result = subprocess.run(["git", "config", "core.hooksPath"], capture_output=True, text=True)

    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    # Default location when core.hooksPath is not configured.
    return ".git/hooks"


def _backup_existing_hook(hook_path: str) -> None:
    """Back up an existing hook file. Skip if backup already exists."""
    if not os.path.exists(hook_path):
        return
    if os.path.exists(hook_path + HOOK_BACKUP_SUFFIX):
        print("There is already a backup of the hook present.")
        print("skipping backup creation")
        return
    os.rename(hook_path, hook_path + HOOK_BACKUP_SUFFIX)


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
        _backup_existing_hook(hook_path)

        with open(hook_path, "w") as f:
            f.write(HOOK_SCRIPT)

        os.chmod(hook_path, mode=0o755)

    except OSError as e:
        return HookResult(success=False, error=str(e))

    return HookResult(success=True)
