import subprocess
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from noidea.cli import app
from noidea.config import LlmConfig
from noidea.git import Commit, DiffResult, HookResult
from noidea.key_store import KeyStoreError
from noidea.provider import ErrorKind, ProviderError

runner = CliRunner()


class TestBuildUserContent:
    """Prompt assembly is pure — testable without touching the API."""

    def test_assembles_branch_files_and_diff(self):
        from noidea.commands.suggest import _build_user_content

        result = _build_user_content("+ added x", "feature/x", ["a.py", "b.py"])
        assert result == ("Branch: feature/x\nStaged files:\n- a.py\n- b.py\n\nDiff:\n+ added x")

    def test_empty_branch_and_files_returns_just_diff(self):
        from noidea.commands.suggest import _build_user_content

        # The test command path: no git context, so the content is the diff alone.
        assert _build_user_content("+ added x", "", []) == "+ added x"

    def test_includes_repo_conventions_when_profile_present(self):
        from noidea.commands.suggest import _build_user_content

        # When style learning produced guidance, it appears before the diff so the model
        # reads the repo's conventions alongside the change.
        result = _build_user_content(
            "+ added x", "main", ["a.py"], "Repo commit conventions:\n- keep it terse"
        )
        assert "Repo commit conventions:\n- keep it terse" in result
        assert result.index("Repo commit conventions:") < result.index("Diff:")

    def test_omits_conventions_when_profile_absent(self):
        from noidea.commands.suggest import _build_user_content

        result = _build_user_content("+ added x", "main", ["a.py"], "")
        assert "Repo commit conventions:" not in result


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
    @patch("noidea.commands.suggest.complete", return_value="fix: patch bug")
    @patch(
        "noidea.commands.suggest.load_config",
        return_value=LlmConfig(system_prompt="gen msg"),
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

    @patch("noidea.commands.suggest.complete", return_value="feat: new thing")
    @patch(
        "noidea.commands.suggest.load_config",
        return_value=LlmConfig(system_prompt="gen msg"),
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

    @patch("noidea.commands.suggest.complete", return_value="fix: thing")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["file.py"])
    @patch("noidea.commands.suggest.load_config", return_value=LlmConfig())
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ change"),
    )
    def test_suggest_model_override_is_used(
        self, mock_diff, mock_config, mock_staged, mock_branch, mock_commit
    ):
        # --model replaces both models, so the override reaches the API regardless of size.
        result = runner.invoke(app, ["suggest", "--model", "claude-opus-4-7"])
        assert result.exit_code == 0
        assert mock_commit.call_args.args[2] == "claude-opus-4-7"

    @patch("noidea.commands.suggest.complete", return_value="feat: thing")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["a.py"])
    @patch("noidea.commands.suggest.load_config", return_value=LlmConfig())
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ change"),
    )
    @patch(
        "noidea.commands.suggest.get_recent_commits",
        return_value=[Commit(f"feat(cli): change {i}", "") for i in range(6)],
    )
    def test_suggest_injects_learned_style_into_prompt(
        self, mock_log, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # With style learning on and real history, the model sees the repo's conventions.
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        user_content = mock_complete.call_args.args[1]
        assert "Repo commit conventions:" in user_content
        assert "cli" in user_content  # the repo's observed scope is surfaced

    @patch("noidea.commands.suggest.complete", return_value="feat: thing")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["a.py"])
    @patch(
        "noidea.commands.suggest.load_config",
        return_value=LlmConfig(learn_commit_style=False),
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ change"),
    )
    @patch("noidea.commands.suggest.get_recent_commits")
    def test_suggest_skips_style_learning_when_disabled(
        self, mock_log, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # The kill-switch must avoid the git-log work entirely, not just drop the section.
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        mock_log.assert_not_called()
        assert "Repo commit conventions:" not in mock_complete.call_args.args[1]

    @patch("noidea.commands.suggest.complete", return_value="feat: thing")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["a.py"])
    @patch("noidea.commands.suggest.load_config", return_value=LlmConfig())
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ change"),
    )
    @patch("noidea.commands.suggest.get_recent_commits", return_value=[])
    def test_suggest_degrades_when_no_history(
        self, mock_log, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # Thin/shallow history yields no profile; suggest still works, just without the section.
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "feat: thing" in result.output  # the mocked message still flows through
        assert "Repo commit conventions:" not in mock_complete.call_args.args[1]


class TestTestCommand:
    @patch("noidea.commands.test.complete", return_value="hello!")
    def test_test_success(self, mock_commit):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "The AI is alive and well" in result.output
        assert "hello!" in result.output

    @patch(
        "noidea.commands.test.complete",
        side_effect=ProviderError(ErrorKind.CONNECTION, "network down"),
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
            "return_value": LlmConfig(system_prompt="gen msg"),
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
            patch("noidea.commands.suggest.complete", side_effect=error),
            patch("noidea.commands.suggest.get_branch_name", return_value="main"),
            patch("noidea.commands.suggest.get_staged_files", return_value=["file.py"]),
        ):
            return runner.invoke(app, ["suggest"])

    def test_suggest_auth_error(self):
        error = ProviderError(ErrorKind.AUTH, "bad key")
        result = self._invoke_suggest_with_api_error(error)
        assert "Authentication failed" in result.output

    def test_suggest_rate_limit_error(self):
        error = ProviderError(ErrorKind.RATE_LIMIT, "slow down")
        result = self._invoke_suggest_with_api_error(error)
        assert "Rate limited" in result.output

    def test_suggest_connection_error(self):
        error = ProviderError(ErrorKind.CONNECTION, "network down")
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
            patch("noidea.commands.suggest.complete", return_value="feat: stuff"),
            patch("noidea.commands.suggest.get_branch_name", return_value="main"),
            patch("noidea.commands.suggest.get_staged_files", return_value=["file.py"]),
        ):
            result = runner.invoke(app, ["suggest", "--file", bad_path])
        assert "Could not write" in result.output


class TestKeysErrors:
    """Error paths in keys commands surface as a single KeyStoreError."""

    def test_show_keys_file_error(self):
        with patch(
            "noidea.commands.keys.key_store.list",
            side_effect=KeyStoreError("read error"),
        ):
            result = runner.invoke(app, ["keys", "show"])
        assert "Couldn't read keys" in result.output

    def test_add_key_keyring_error(self):
        with patch("noidea.commands.keys.key_store.add", side_effect=KeyStoreError("locked")):
            result = runner.invoke(app, ["keys", "add"], input="secret\n")
        assert "Couldn't save the key" in result.output

    def test_remove_key_keyring_error(self):
        with patch("noidea.commands.keys.key_store.remove", side_effect=KeyStoreError("locked")):
            result = runner.invoke(app, ["keys", "remove", "anthropic"])
        assert "Couldn't remove the key" in result.output


class TestKeysAdd:
    @patch("noidea.commands.keys.key_store.add", return_value=True)
    def test_add_key(self, mock_add):
        result = runner.invoke(app, ["keys", "add"], input="secret-key\n")
        assert result.exit_code == 0
        assert "Key saved" in result.output
        mock_add.assert_called_once_with("anthropic", "secret-key")

    @patch("noidea.commands.keys.key_store.add", return_value=False)
    def test_add_key_already_exists(self, mock_add):
        result = runner.invoke(app, ["keys", "add"], input="secret-key\n")
        assert result.exit_code == 0
        assert "already have a key" in result.output


class TestKeysRemove:
    @patch("noidea.commands.keys.key_store.remove", return_value=True)
    def test_remove_key(self, mock_remove):
        result = runner.invoke(app, ["keys", "remove", "anthropic"])
        assert result.exit_code == 0
        assert "Key removed" in result.output
        mock_remove.assert_called_once_with("anthropic")

    @patch("noidea.commands.keys.key_store.remove", return_value=False)
    def test_remove_key_not_found(self, mock_remove):
        result = runner.invoke(app, ["keys", "remove", "anthropic"])
        assert result.exit_code == 0
        assert "Key not found" in result.output


class TestKeysList:
    @patch("noidea.commands.keys.key_store.list", return_value=["anthropic"])
    def test_list_keys(self, mock_list):
        result = runner.invoke(app, ["keys", "show"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
        mock_list.assert_called_once()
