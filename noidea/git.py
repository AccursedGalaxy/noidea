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


HOOK_BACKUP_SUFFIX = ".bak"

# The hooks noidea installs, name → script. prepare-commit-msg writes the message into the
# commit buffer (seeding a queued agent proposal when one exists, else the fast single-shot —
# see suggest.suggest). post-commit reconciles the committed message against any seeded agent
# proposal to capture the accept/edit/discard signal (see dogfood.reconcile). post-commit's
# exit status is ignored by git, so reconcile can never block a commit.
HOOKS = {
    "prepare-commit-msg": '#!/bin/bash\nnoidea suggest --file "$1"\n',
    "post-commit": "#!/bin/bash\nnoidea _reconcile\n",
}

# TigerStyle: compile-time-style constant assertion — every hook must carry a real script.
if not all(script.strip() for script in HOOKS.values()):
    raise RuntimeError("every HOOKS script must be non-empty")


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


def get_commit_message(ref: str = "HEAD") -> str:
    """Return the full commit message (subject + body) of a ref; "" on any failure.

    Best-effort like the other wrappers: the post-commit reconcile reads this and must
    never crash the commit, so a missing ref or absent git degrades to an empty string.
    """
    assert isinstance(ref, str) and ref, "ref must be a non-empty string"
    result = subprocess.run(
        ["git", "log", "-1", "--format=%B", ref],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_head_sha() -> str:
    """Return HEAD's full commit SHA, or "" if there is no commit yet / git is missing."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    sha = result.stdout.strip() if result.returncode == 0 else ""
    assert isinstance(sha, str), "sha must be a string"
    return sha


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
        result = subprocess.run(
            ["git", "diff", "--staged"], capture_output=True, check=True
        )

        if not result.stdout:
            return DiffResult(has_changes=False)

        # Decode with replace to survive any stray non-UTF-8 bytes.
        diff_text = result.stdout.decode("utf-8", errors="replace")
        diff_text = _strip_binary_hunks(diff_text)

        assert isinstance(diff_text, str), "diff must be a string after processing"
        return DiffResult(has_changes=True, diff=diff_text)

    except subprocess.CalledProcessError as e:
        return DiffResult(
            has_changes=False, error=e.stderr.decode("utf-8", errors="replace")
        )

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


def _backup_existing_hook(hook_path: str) -> None:
    """Back up an existing hook file. Skip if backup already exists."""
    if not os.path.exists(hook_path):
        return
    if os.path.exists(hook_path + HOOK_BACKUP_SUFFIX):
        print("There is already a backup of the hook present.")
        print("skipping backup creation")
        return
    os.rename(hook_path, hook_path + HOOK_BACKUP_SUFFIX)


def _write_hook(hooks_dir: str, name: str, script: str) -> None:
    """Back up any existing hook of this name, then write ours and make it executable."""
    assert isinstance(name, str) and name, "hook name must be non-empty"
    assert isinstance(script, str) and script.strip(), "hook script must be non-empty"
    hook_path = os.path.join(hooks_dir, name)
    _backup_existing_hook(hook_path)
    with open(hook_path, "w") as f:
        f.write(script)
    os.chmod(hook_path, mode=0o755)


def install_hook() -> HookResult:
    hooks_dir = get_hooks_dir()

    if hooks_dir is None:
        return HookResult(success=False, error="Not inside a git repository")

    # TigerStyle: validate data from external source (git subprocess).
    if not isinstance(hooks_dir, str) or not hooks_dir.strip():
        return HookResult(success=False, error="hooks_dir is empty or invalid")

    # Install every hook in HOOKS; the first failure aborts so we never leave a half-wired
    # setup (e.g. prepare-commit-msg present but post-commit missing, which would seed agent
    # proposals but never capture the human verdict).
    try:
        os.makedirs(hooks_dir, exist_ok=True)
        for name, script in HOOKS.items():
            _write_hook(hooks_dir, name, script)
    except OSError as e:
        return HookResult(success=False, error=str(e))

    return HookResult(success=True)
