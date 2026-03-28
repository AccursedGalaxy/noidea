import os
from unittest.mock import MagicMock, patch

from noidea.git import get_diff, get_hooks_dir, install_hook


def test_get_diff_nothing_staged():
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("noidea.git.subprocess.run", return_value=mock_result):
        result = get_diff()

    assert not result.has_changes


def test_get_diff_with_staged_changes():
    mock_result = MagicMock()
    mock_result.stdout = "deff --git a/foo.py b/foo.py\n+some change"

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
    assert hook_path.read_text() == '#!/bin/bash\nnoidea suggest --file "$1"\n'
    assert os.access(hook_path, os.X_OK)


def test_install_hook_backs_up_existing(tmp_path):
    hook_path = tmp_path / "prepare-commit-msg"
    hook_path.write_text("#!/bin/bash\necho old hook\n")

    with patch("noidea.git.get_hooks_dir", return_value=str(tmp_path)):
        install_hook()

    backup_path = tmp_path / "prepare-commit-msg.bak"
    assert backup_path.exists()
    assert backup_path.read_text() == "#!/bin/bash\necho old hook\n"
    assert hook_path.read_text() == '#!/bin/bash\nnoidea suggest --file "$1"\n'


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

    error = subprocess.CalledProcessError(128, "git", stderr="fatal: not a git repo")
    with patch("noidea.git.subprocess.run", side_effect=error):
        result = get_diff()
    assert not result.has_changes
    assert result.error == "fatal: not a git repo"


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
