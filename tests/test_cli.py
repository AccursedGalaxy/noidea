import subprocess
from unittest.mock import MagicMock, patch

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
            }
        },
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ new feature"),
    )
    def test_suggest_writes_to_file(
        self, mock_diff, mock_config, mock_commit, tmp_path
    ):
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
        side_effect=Exception("API error"),
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
