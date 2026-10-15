import os
import subprocess
from unittest.mock import MagicMock, patch

from noidea.git import (
    HOOKS,
    Commit,
    HookOutcome,
    _strip_binary_hunks,
    get_diff,
    get_hooks_dir,
    get_recent_commits,
    install_hook,
    is_noidea_hook,
    uninstall_hooks,
)


def test_get_recent_commits_parses_subjects_and_bodies():
    """Recent commits are parsed into Commit objects with subject and body split out,
    so the style analysis can read them without knowing the git log format."""
    # Records terminated by 0x1e; subject and body separated by 0x1f (matches the format).
    stdout = (
        "feat(cli): add suggest\x1fwhy it was added\nmore detail\x1e"
        "fix: handle empty diff\x1f\x1e"
    )
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = stdout

    with patch("noidea.git.subprocess.run", return_value=mock_result):
        commits = get_recent_commits(50)

    assert commits == [
        Commit("feat(cli): add suggest", "why it was added\nmore detail"),
        Commit("fix: handle empty diff", ""),
    ]


def test_get_recent_commits_degrades_to_empty_and_never_raises():
    """Any failure (git error exit, or git not installed) yields an empty list rather
    than raising, because the prepare-commit-msg hook aborts the commit on a crash."""
    failed = MagicMock()
    failed.returncode = 128
    failed.stdout = ""
    with patch("noidea.git.subprocess.run", return_value=failed):
        assert get_recent_commits(50) == []

    with patch("noidea.git.subprocess.run", side_effect=FileNotFoundError("git missing")):
        assert get_recent_commits(50) == []


def test_get_diff_nothing_staged():
    mock_result = MagicMock()
    # subprocess.run runs without text=True, so stdout is bytes.
    mock_result.stdout = b""

    with patch("noidea.git.subprocess.run", return_value=mock_result):
        result = get_diff()

    assert not result.has_changes


def test_get_diff_with_staged_changes():
    mock_result = MagicMock()
    mock_result.stdout = b"deff --git a/foo.py b/foo.py\n+some change"

    with patch("noidea.git.subprocess.run", return_value=mock_result):
        result = get_diff()

    assert result.has_changes
    assert result.diff == "deff --git a/foo.py b/foo.py\n+some change"


def test_get_hooks_dir_no_dir_found():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with (
        patch("noidea.git.is_git_repo", return_value=True),
        patch("noidea.git.subprocess.run", return_value=mock_result),
    ):
        result = get_hooks_dir()

    assert result == ".git/hooks"


def test_get_hooks_dir_dir_found():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "/some/custom/path\n"

    with (
        patch("noidea.git.is_git_repo", return_value=True),
        patch("noidea.git.subprocess.run", return_value=mock_result),
    ):
        result = get_hooks_dir()

    assert result == "/some/custom/path"


def test_install_hook(tmp_path):
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()

    hook_path = tmp_path / "prepare-commit-msg"

    assert hook_path.exists()
    assert hook_path.read_text() == HOOKS["prepare-commit-msg"]
    assert os.access(hook_path, os.X_OK)


def test_install_hook_backs_up_existing(tmp_path):
    hook_path = tmp_path / "prepare-commit-msg"
    hook_path.write_text("#!/bin/bash\necho old hook\n")

    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()

    backup_path = tmp_path / "prepare-commit-msg.bak"
    assert backup_path.exists()
    assert backup_path.read_text() == "#!/bin/bash\necho old hook\n"
    assert hook_path.read_text() == HOOKS["prepare-commit-msg"]


def test_install_hook_empty_hooks_dir():
    with patch("noidea.git.get_hooks_dir", return_value=""):
        result = install_hook()
    assert not result.success
    assert "empty" in result.error.lower() or "invalid" in result.error.lower()


def test_install_hook_whitespace_hooks_dir():
    with patch("noidea.git.get_hooks_dir", return_value="   "):
        result = install_hook()
    assert not result.success


def test_get_diff_git_not_found():
    with patch("noidea.git.subprocess.run", side_effect=FileNotFoundError("git not found")):
        result = get_diff()
    assert not result.has_changes
    assert "git not found" in result.error


def test_get_diff_git_command_fails():
    import subprocess

    error = subprocess.CalledProcessError(128, "git", stderr=b"fatal: not a git repo")
    with patch("noidea.git.subprocess.run", side_effect=error):
        result = get_diff()
    assert not result.has_changes
    assert result.error == "fatal: not a git repo"


def test_strip_binary_hunks_omits_binary_payload():
    diff = (
        "diff --git a/logo.png b/logo.png\n"
        "new file mode 100644\n"
        "index 0000000..abc1234\n"
        "Binary files /dev/null and b/logo.png differ\n"
    )
    cleaned = _strip_binary_hunks(diff)
    assert "diff --git a/logo.png b/logo.png" in cleaned
    assert "[binary file — diff omitted]" in cleaned
    assert "Binary files" not in cleaned


def test_strip_binary_hunks_keeps_text_diffs():
    diff = "diff --git a/foo.py b/foo.py\n@@ -1 +1 @@\n-old\n+new\n"
    cleaned = _strip_binary_hunks(diff)
    assert cleaned == diff


def test_strip_binary_hunks_mixed_keeps_text_strips_binary():
    diff = (
        "diff --git a/foo.py b/foo.py\n@@ -1 +1 @@\n-old\n+new\n"
        "diff --git a/logo.png b/logo.png\n"
        "Binary files a/logo.png and b/logo.png differ\n"
    )
    cleaned = _strip_binary_hunks(diff)
    assert "+new" in cleaned
    assert "[binary file — diff omitted]" in cleaned
    assert "Binary files" not in cleaned


def test_get_diff_strips_binary_and_survives_bad_bytes():
    mock_result = MagicMock()
    # Invalid UTF-8 byte (0xff) plus a binary hunk: must not crash.
    mock_result.stdout = (
        b"diff --git a/logo.png b/logo.png\n" b"Binary files a/logo.png and b/logo.png differ\xff\n"
    )
    with patch("noidea.git.subprocess.run", return_value=mock_result):
        result = get_diff()
    assert result.has_changes
    assert "[binary file — diff omitted]" in result.diff
    assert "Binary files" not in result.diff


def test_install_hook_not_in_repo():
    with patch("noidea.git.get_hooks_dir", return_value=None):
        result = install_hook()
    assert not result.success
    assert "Not inside a git repository" in result.error


def test_install_hook_makedirs_failure():
    with (
        patch("noidea.git.get_hooks_dir", return_value="/fake/hooks"),
        patch("noidea.git.os.makedirs", side_effect=OSError("Permission denied")),
    ):
        result = install_hook()
    assert not result.success
    assert "Permission denied" in result.error


def test_install_hook_fresh_reports_installed(tmp_path):
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        result = install_hook()
    assert result.success
    assert result.outcome is HookOutcome.INSTALLED


def test_install_hook_rerun_reports_up_to_date(tmp_path):
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()
        result = install_hook()
    assert result.success
    assert result.outcome is HookOutcome.UNCHANGED
    # Our own hook is never backed up: a .bak of noidea would shadow a real user hook backup.
    assert not (tmp_path / "prepare-commit-msg.bak").exists()


def test_install_hook_replacing_an_older_noidea_hook_reports_updated(tmp_path, capsys):
    # The pre-1.3 hook: noidea's, but without the message source forwarded.
    old_hook = tmp_path / "prepare-commit-msg"
    old_hook.write_text('#!/bin/bash\nnoidea suggest --file "$1"\n')
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        result = install_hook()
    assert result.success
    assert result.outcome is HookOutcome.UPDATED
    assert old_hook.read_text() == HOOKS["prepare-commit-msg"]
    assert not (tmp_path / "prepare-commit-msg.bak").exists()
    assert "backup" not in capsys.readouterr().out


def test_install_hook_over_a_foreign_hook_reports_installed(tmp_path):
    (tmp_path / "prepare-commit-msg").write_text("#!/bin/bash\necho mine\n")
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        result = install_hook()
    assert result.outcome is HookOutcome.INSTALLED
    assert (tmp_path / "prepare-commit-msg.bak").read_text() == "#!/bin/bash\necho mine\n"


def _run_hook(tmp_path, name, *arguments):
    """Run a managed hook script from a repo root with a fake `noidea` on PATH; return its calls."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    calls = tmp_path / "calls.txt"
    calls.unlink(missing_ok=True)
    fake = bin_dir / "noidea"
    fake.write_text(f'#!/bin/bash\necho "$@" >> {calls}\n')
    fake.chmod(0o755)
    hook = tmp_path / name
    hook.write_text(HOOKS[name])
    hook.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    subprocess.run([str(hook), *arguments], cwd=tmp_path, env=env, check=True)
    return calls.read_text() if calls.exists() else ""


def _run_post_commit_hook(tmp_path):
    return _run_hook(tmp_path, "post-commit")


def _write_seed(tmp_path):
    from noidea.dogfood import _seeded_path

    seeded = _seeded_path(str(tmp_path))
    os.makedirs(os.path.dirname(seeded), exist_ok=True)
    with open(seeded, "w") as handle:
        handle.write("{}")
    return seeded


def test_prepare_hook_skips_python_for_a_supplied_message(tmp_path):
    # -m, --amend, merges, and squashes keep their message, so the hook decides that in the
    # shell rather than paying ~0.5 s of Python startup to reach the same conclusion. It still
    # drops a stale seed pointer so post-commit cannot mis-reconcile the hand-written message.
    for source in ("message", "commit", "merge", "squash"):
        seeded = _write_seed(tmp_path)
        assert _run_hook(tmp_path, "prepare-commit-msg", "MSG", source) == ""
        assert not os.path.exists(seeded)


def test_prepare_hook_generates_for_plain_and_template_commits(tmp_path):
    for arguments in (("MSG",), ("MSG", "template")):
        calls = _run_hook(tmp_path, "prepare-commit-msg", *arguments)
        assert calls.startswith("suggest --file MSG --source")


def test_post_commit_hook_skips_python_when_nothing_was_seeded(tmp_path):
    # Every commit runs this hook; starting Python costs ~0.5 s, so a commit with no seeded
    # agent proposal (the common case) must exit in the shell without invoking noidea.
    assert _run_post_commit_hook(tmp_path) == ""


def test_post_commit_hook_reconciles_when_a_proposal_was_seeded(tmp_path):
    _write_seed(tmp_path)
    assert _run_post_commit_hook(tmp_path) == "_reconcile\n"


# ---- ownership & uninstall ----


def test_only_exact_noidea_scripts_count_as_ours():
    # Every script noidea has ever written, current and previous, is recognised.
    assert is_noidea_hook('#!/bin/bash\nnoidea suggest --file "$1"\n')
    assert is_noidea_hook("#!/bin/bash\nnoidea _reconcile\n")
    assert all(is_noidea_hook(script) for script in HOOKS.values())
    # A hand-edited hook is the user's, even when it still calls noidea: overwriting or
    # deleting it would silently lose their edits.
    assert not is_noidea_hook('#!/bin/bash\nnoidea suggest --file "$1"\nmake lint\n')
    assert not is_noidea_hook("#!/bin/bash\necho mine\n")


def test_install_backs_up_a_hand_edited_noidea_hook(tmp_path):
    edited = '#!/bin/bash\nnoidea suggest --file "$1"\nmake lint\n'
    (tmp_path / "prepare-commit-msg").write_text(edited)
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()
    assert (tmp_path / "prepare-commit-msg.bak").read_text() == edited


def test_uninstall_removes_our_hooks(tmp_path):
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()
        result = uninstall_hooks()
    assert result.success
    assert sorted(result.removed) == sorted(HOOKS)
    assert result.restored == [] and result.skipped == []
    assert not any((tmp_path / name).exists() for name in HOOKS)


def test_uninstall_restores_the_backed_up_user_hook(tmp_path):
    (tmp_path / "prepare-commit-msg").write_text("#!/bin/bash\necho mine\n")
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()
        result = uninstall_hooks()
    assert result.restored == ["prepare-commit-msg"]
    assert (tmp_path / "prepare-commit-msg").read_text() == "#!/bin/bash\necho mine\n"
    assert not (tmp_path / "prepare-commit-msg.bak").exists()


def test_uninstall_leaves_a_hook_noidea_did_not_write(tmp_path):
    (tmp_path / "post-commit").write_text("#!/bin/bash\necho mine\n")
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        result = uninstall_hooks()
    assert result.skipped == ["post-commit"]
    assert result.removed == []
    assert (tmp_path / "post-commit").read_text() == "#!/bin/bash\necho mine\n"


def test_uninstall_outside_a_repo_fails():
    with patch("noidea.git.get_hooks_dir", return_value=None):
        result = uninstall_hooks()
    assert not result.success
    assert "Not inside a git repository" in result.error


def test_install_refuses_to_overwrite_a_foreign_hook_when_a_backup_exists(tmp_path):
    # Backing up would clobber the existing .bak and installing would clobber the hook, so
    # either way a user's script is lost. Refuse and say why instead.
    (tmp_path / "prepare-commit-msg").write_text("#!/bin/bash\necho second\n")
    (tmp_path / "prepare-commit-msg.bak").write_text("#!/bin/bash\necho first\n")
    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        result = install_hook()
    assert not result.success
    assert "prepare-commit-msg.bak" in result.error
    assert (tmp_path / "prepare-commit-msg").read_text() == "#!/bin/bash\necho second\n"
    assert (tmp_path / "prepare-commit-msg.bak").read_text() == "#!/bin/bash\necho first\n"
