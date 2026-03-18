import subprocess
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from noidea.cli import app

runner = CliRunner()


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "noidea" in result.output


class TestInit:
    @patch("noidea.cli.install_hook")
    def test_init_installs_hook(self, mock_install):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Git hook installed successfully" in result.output
        mock_install.assert_called_once()


class TestSuggest:
    @patch("noidea.cli.get_commit_message", return_value="fix: patch bug")
    @patch(
        "noidea.cli.load_config",
        return_value={
            "llm": {
                "system_prompt": "gen msg",
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
            }
        },
    )
    @patch("noidea.cli.get_diff", return_value="+ some change")
    def test_suggest_prints_message(self, mock_diff, mock_config, mock_commit):
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "fix: patch bug" in result.output

    @patch("noidea.cli.get_diff", return_value="none")
    def test_suggest_no_changes(self, mock_diff):
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "No Changes" in result.output

    @patch("noidea.cli.get_commit_message", return_value="feat: new thing")
    @patch(
        "noidea.cli.load_config",
        return_value={
            "llm": {
                "system_prompt": "gen msg",
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
            }
        },
    )
    @patch("noidea.cli.get_diff", return_value="+ new feature")
    def test_suggest_writes_to_file(
        self, mock_diff, mock_config, mock_commit, tmp_path
    ):
        outfile = str(tmp_path / "msg.txt")
        result = runner.invoke(app, ["suggest", "--file", outfile])
        assert result.exit_code == 0
        with open(outfile) as f:
            assert f.read() == "feat: new thing"


class TestTestCommand:
    @patch("noidea.cli.get_commit_message", return_value="hello!")
    def test_test_success(self, mock_commit):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "Test successful!" in result.output
        assert "hello!" in result.output

    @patch("noidea.cli.get_commit_message", side_effect=Exception("API error"))
    def test_test_failure(self, mock_commit):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "Something went wrong" in result.output


class TestUpdate:
    @patch("noidea.cli.subprocess.run")
    def test_update_with_pipx(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(["pipx", "upgrade", "noidea"], check=True)

    @patch("noidea.cli.subprocess.run")
    def test_update_falls_back_to_pip(self, mock_run):
        # First call raises FileNotFoundError (pipx missing), second succeeds (pip)
        mock_run.side_effect = [FileNotFoundError, MagicMock(returncode=0)]
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0

    @patch(
        "noidea.cli.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "pipx"),
    )
    def test_update_handles_failure(self, mock_run):
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 1


class TestKeysAdd:
    @patch("noidea.cli.save_key")
    @patch("noidea.cli.keyring")
    def test_add_key(self, mock_keyring, mock_save):
        result = runner.invoke(app, ["keys", "add"], input="secret-key\n")
        assert result.exit_code == 0
        assert "API key saved" in result.output
        mock_keyring.set_password.assert_called_once_with(
            service_name="noidea", username="Anthropic", password="secret-key"
        )
        mock_save.assert_called_once_with("Anthropic")


class TestKeysRemove:
    @patch("noidea.cli.remove_key")
    @patch("noidea.cli.keyring")
    def test_remove_key(self, mock_keyring, mock_remove):
        result = runner.invoke(app, ["keys", "remove"], input="Anthropic\n")
        assert result.exit_code == 0
        assert "Key deleted" in result.output
        mock_keyring.delete_password.assert_called_once_with(
            service_name="noidea", username="Anthropic"
        )
        mock_remove.assert_called_once_with("Anthropic")


class TestKeysList:
    @patch("noidea.cli.list_keys")
    def test_list_keys(self, mock_list):
        result = runner.invoke(app, ["keys", "list"])
        assert result.exit_code == 0
        mock_list.assert_called_once()
