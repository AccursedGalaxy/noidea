import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("noidea")
except PackageNotFoundError:
    __version__ = "0.0.0"


def _run_git(repo_root: Path, *args: str) -> str | None:
    """Run one git command in repo_root, returning stripped stdout or None on any failure.

    Any git problem — missing binary, not a repo, non-zero exit, timeout — means we simply
    cannot enrich the version, so it collapses to None and the caller falls back cleanly.
    """
    assert isinstance(repo_root, Path), "repo_root must be a Path"
    assert args, "at least one git argument is required"
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or None


def build_version() -> str:
    """The version to display: the released string, plus a git commit tag for source builds.

    A wheel/PyPI install has no .git beside its source, so released users always see the clean
    metadata version. A source checkout (editable/dev build) shows '<version>+<short_hash>[.dirty]'
    unless HEAD sits exactly on the matching release tag with a clean tree — that IS a released
    build. Git runs here, on demand, never at import, so the CLI's hot path pays nothing for it.
    """
    base_version = __version__
    assert isinstance(base_version, str) and base_version, (
        "base version must be non-empty"
    )
    # The package lives at <repo_root>/noidea/__init__.py; a released wheel has no sibling .git.
    repo_root = Path(__file__).resolve().parent.parent
    if not (repo_root / ".git").exists():
        return base_version
    short_hash = _run_git(repo_root, "rev-parse", "--short", "HEAD")
    if short_hash is None:
        return base_version
    dirty = _run_git(repo_root, "status", "--porcelain") is not None
    # An exact, clean match on the release tag means this checkout is the released build itself.
    on_release_tag = _run_git(repo_root, "describe", "--tags", "--exact-match") in (
        f"v{base_version}",
        base_version,
    )
    if on_release_tag and not dirty:
        return base_version
    result = (
        f"{base_version}+{short_hash}.dirty"
        if dirty
        else f"{base_version}+{short_hash}"
    )
    assert result.startswith(base_version), "build version must extend the base version"
    return result
