import subprocess
from unittest.mock import MagicMock, patch

import anthropic
from typer.testing import CliRunner

from noidea.cli import app
from noidea.git import DiffResult, HookResult

runner = CliRunner()


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "noidea" in result.output


class TestInit:
    @patch("noidea.commands.init.install_hook", return_value=HookResult(success=True))
    def test_init_installs_hook(self, mock_install):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Hook installed" in result.output
        mock_install.assert_called_once()


class TestSuggest:
    @patch("noidea.commands.suggest.get_commit_message", return_value="fix: patch bug")
    @patch(
        "noidea.commands.suggest.load_config",
        return_value={
            "llm": {
                "system_prompt": "gen msg",
                "small_model": "claude-haiku-4-5",
                "large_model": "claude-sonnet-4-6",
                "context_limit": 600000,
                "max_tokens": 1024,
                "temperature": 1.0,
            }
        },
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ some change"),
    )
    def test_suggest_prints_message(self, mock_diff, mock_config, mock_commit):
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "fix: patch bug" in result.output

    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=False),
    )
    def test_suggest_no_changes(self, mock_diff):
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "Nothing staged" in result.output

    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="   \n  "),
    )
    def test_suggest_empty_diff_content(self, mock_diff):
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "empty diff" in result.output.lower()

    @patch("noidea.commands.suggest.get_commit_message", return_value="feat: new thing")
    @patch(
        "noidea.commands.suggest.load_config",
        return_value={
            "llm": {
                "system_prompt": "gen msg",
                "small_model": "claude-haiku-4-5",
                "large_model": "claude-sonnet-4-6",
                "context_limit": 600000,
                "max_tokens": 1024,
                "temperature": 1.0,
            }
        },
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ new feature"),
    )
    def test_suggest_writes_to_file(self, mock_diff, mock_config, mock_commit, tmp_path):
        outfile = str(tmp_path / "msg.txt")
        result = runner.invoke(app, ["suggest", "--file", outfile])
        assert result.exit_code == 0
        with open(outfile) as f:
            assert f.read() == "feat: new thing"


class TestTestCommand:
    @patch("noidea.commands.test.get_commit_message", return_value="hello!")
    def test_test_success(self, mock_commit):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "The AI is alive and well" in result.output
        assert "hello!" in result.output

    @patch(
        "noidea.commands.test.get_commit_message",
        side_effect=anthropic.APIConnectionError(request=None),
    )
    def test_test_failure(self, mock_commit):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "Couldn't reach the API" in result.output


class TestUpdate:
    @patch("noidea.commands.update.subprocess.run")
    def test_update_with_pipx(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(["pipx", "upgrade", "noidea"], check=True)

    @patch("noidea.commands.update.subprocess.run")
    def test_update_falls_back_to_pip(self, mock_run):
        # First call raises FileNotFoundError (pipx missing), second succeeds (pip)
        mock_run.side_effect = [FileNotFoundError, MagicMock(returncode=0)]
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0

    @patch(
        "noidea.commands.update.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "pipx"),
    )
    def test_update_handles_failure(self, mock_run):
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 1


class TestSuggestErrors:
    """API and I/O error paths in the suggest command."""

    _SUGGEST_MOCKS = {
        "noidea.commands.suggest.load_config": {
            "return_value": {
                "llm": {
                    "system_prompt": "gen msg",
                    "small_model": "claude-haiku-4-5",
                    "large_model": "claude-sonnet-4-6",
                    "context_limit": 600000,
                    "max_tokens": 1024,
                    "temperature": 1.0,
                }
            }
        },
        "noidea.commands.suggest.get_diff": {
            "return_value": DiffResult(has_changes=True, diff="+ change"),
        },
    }

    def _invoke_suggest_with_api_error(self, error):
        with (
            patch(
                **{
                    "target": "noidea.commands.suggest.load_config",
                    **self._SUGGEST_MOCKS["noidea.commands.suggest.load_config"],
                }
            ),
            patch(
                **{
                    "target": "noidea.commands.suggest.get_diff",
                    **self._SUGGEST_MOCKS["noidea.commands.suggest.get_diff"],
                }
            ),
            patch("noidea.commands.suggest.get_commit_message", side_effect=error),
            patch("noidea.commands.suggest.get_branch_name", return_value="main"),
            patch("noidea.commands.suggest.get_staged_files", return_value=["file.py"]),
        ):
            return runner.invoke(app, ["suggest"])

    def test_suggest_auth_error(self):
        error = anthropic.AuthenticationError(
            message="bad key", response=MagicMock(status_code=401), body={}
        )
        result = self._invoke_suggest_with_api_error(error)
        assert "Authentication failed" in result.output

    def test_suggest_rate_limit_error(self):
        error = anthropic.RateLimitError(
            message="slow down", response=MagicMock(status_code=429), body={}
        )
        result = self._invoke_suggest_with_api_error(error)
        assert "Rate limited" in result.output

    def test_suggest_connection_error(self):
        error = anthropic.APIConnectionError(request=None)
        result = self._invoke_suggest_with_api_error(error)
        assert "Could not connect" in result.output

    def test_suggest_file_write_error(self, tmp_path):
        bad_path = str(tmp_path / "no" / "such" / "dir" / "msg.txt")
        with (
            patch(
                **{
                    "target": "noidea.commands.suggest.load_config",
                    **self._SUGGEST_MOCKS["noidea.commands.suggest.load_config"],
                }
            ),
            patch(
                **{
                    "target": "noidea.commands.suggest.get_diff",
                    **self._SUGGEST_MOCKS["noidea.commands.suggest.get_diff"],
                }
            ),
            patch("noidea.commands.suggest.get_commit_message", return_value="feat: stuff"),
            patch("noidea.commands.suggest.get_branch_name", return_value="main"),
            patch("noidea.commands.suggest.get_staged_files", return_value=["file.py"]),
        ):
            result = runner.invoke(app, ["suggest", "--file", bad_path])
        assert "Could not write" in result.output


class TestKeysErrors:
    """Error paths in keys commands."""

    def test_show_keys_file_error(self):
        with patch("noidea.commands.keys.list_keys", side_effect=OSError("read error")):
            result = runner.invoke(app, ["keys", "show"])
        assert "Couldn't read keys" in result.output

    def test_add_key_keyring_error(self):
        import keyring.errors

        with (
            patch(
                "noidea.commands.keys.keyring.set_password",
                side_effect=keyring.errors.KeyringError("locked"),
            ),
        ):
            result = runner.invoke(app, ["keys", "add"], input="secret\n")
        assert "Couldn't save the key" in result.output

    def test_remove_key_keyring_error(self):
        import keyring.errors

        with (
            patch(
                "noidea.commands.keys.keyring.delete_password",
                side_effect=keyring.errors.KeyringError("locked"),
            ),
        ):
            result = runner.invoke(app, ["keys", "remove", "anthropic"])
        assert "Couldn't remove the key" in result.output


class TestKeysAdd:
    @patch("noidea.commands.keys.save_key")
    @patch("noidea.commands.keys.keyring")
    def test_add_key(self, mock_keyring, mock_save):
        result = runner.invoke(app, ["keys", "add"], input="secret-key\n")
        assert result.exit_code == 0
        assert "Key saved" in result.output
        mock_keyring.set_password.assert_called_once_with(
            service_name="noidea", username="anthropic", password="secret-key"
        )
        mock_save.assert_called_once_with("anthropic")


class TestKeysRemove:
    @patch("noidea.commands.keys.remove_key")
    @patch("noidea.commands.keys.keyring")
    def test_remove_key(self, mock_keyring, mock_remove):
        result = runner.invoke(app, ["keys", "remove", "anthropic"])
        assert result.exit_code == 0
        assert "Key removed" in result.output
        mock_keyring.delete_password.assert_called_once_with(
            service_name="noidea", username="anthropic"
        )
        mock_remove.assert_called_once_with("anthropic")


class TestKeysList:
    @patch("noidea.commands.keys.list_keys")
    def test_list_keys(self, mock_list):
        result = runner.invoke(app, ["keys", "show"])
        assert result.exit_code == 0
        mock_list.assert_called_once()
