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
        assert result == (
            "Branch: feature/x\nStaged files:\n- a.py\n- b.py\n\nDiff:\n+ added x"
        )

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


class TestCapDiff:
    """The diff sent to the model is bounded so an enormous staged change (generated artifacts,
    vendored trees) can't blow past the provider's context window and fail the whole request."""

    def test_diff_within_cap_is_returned_unchanged(self):
        from noidea.commands.suggest import _cap_diff

        diff = "+ small change\n"
        assert _cap_diff(diff, 200000) == diff

    def test_diff_exactly_at_cap_is_unchanged(self):
        from noidea.commands.suggest import _cap_diff

        diff = "x" * 500
        assert _cap_diff(diff, 500) == diff

    def test_oversized_diff_is_truncated_with_a_notice(self):
        from noidea.commands.suggest import _cap_diff

        diff = "x" * 1000
        result = _cap_diff(diff, 400)
        # The head up to the cap is preserved so the model still sees real diff content.
        assert result.startswith("x" * 400)
        # The dropped bytes are named so the model (and reader) know the diff was cut.
        assert "truncated" in result
        assert "600" in result  # 1000 - 400 characters omitted.

    def test_truncation_keeps_payload_bounded(self):
        from noidea.commands.suggest import _cap_diff

        # A 5 MB diff must collapse to roughly the cap plus a short notice, never the full size.
        diff = "d" * 5_000_000
        result = _cap_diff(diff, 200000)
        assert len(result) < 201000


class TestDiffBudgetChars:
    """The per-model budget: a big-window model gets a large diff allowance, a small one a small
    allowance, and an explicit config cap overrides both downward for cost control."""

    def test_large_window_model_gets_a_large_budget(self):
        from noidea.commands.suggest import _diff_budget_chars

        # gemini's ~1M window yields a multi-MB char budget, so normal diffs are never truncated.
        budget = _diff_budget_chars(
            "google/gemini-2.5-flash", LlmConfig(diff_chars_max=0)
        )
        assert budget > 2_000_000

    def test_small_window_model_gets_a_small_budget(self):
        from noidea.commands.suggest import _diff_budget_chars

        # gpt-4o-mini's 128k window must yield a far smaller budget so a mis-routed diff still fits.
        budget = _diff_budget_chars("openai/gpt-4o-mini", LlmConfig(diff_chars_max=0))
        assert budget < 500_000
        assert budget > 0

    def test_positive_config_cap_overrides_the_window_budget(self):
        from noidea.commands.suggest import _diff_budget_chars

        # A user who sets diff_chars_max caps below the window-derived budget, never above it.
        budget = _diff_budget_chars(
            "google/gemini-2.5-flash", LlmConfig(diff_chars_max=50_000)
        )
        assert budget == 50_000


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "noidea" in result.output


class TestBuildVersion:
    """build_version() shows the released string for wheels, and enriches source builds with the
    git commit so any commit is identifiable — without paying git's cost on the CLI's hot path."""

    @patch("noidea.Path.exists", return_value=False)
    def test_released_wheel_without_git_shows_plain_version(self, mock_exists):
        # A wheel/PyPI install has no .git beside its source, so users see only the clean version.
        from noidea import __version__, build_version

        assert build_version() == __version__

    @patch("noidea._run_git")
    @patch("noidea.Path.exists", return_value=True)
    def test_clean_checkout_on_release_tag_shows_plain_version(
        self, mock_exists, mock_git
    ):
        # HEAD exactly on the matching tag with a clean tree IS the released build: no commit tag.
        from noidea import __version__, build_version

        def fake_git(repo_root, *args):
            if args[0] == "rev-parse":
                return "abc1234"
            if args[0] == "status":
                return None  # Clean tree: git status --porcelain prints nothing.
            if args[0] == "describe":
                return f"v{__version__}"
            return None

        mock_git.side_effect = fake_git
        assert build_version() == __version__

    @patch("noidea._run_git")
    @patch("noidea.Path.exists", return_value=True)
    def test_clean_dev_commit_appends_short_hash(self, mock_exists, mock_git):
        from noidea import __version__, build_version

        def fake_git(repo_root, *args):
            if args[0] == "rev-parse":
                return "abc1234"
            if args[0] == "status":
                return None
            if args[0] == "describe":
                return None  # Not on any tag: a build from an arbitrary commit.
            return None

        mock_git.side_effect = fake_git
        assert build_version() == f"{__version__}+abc1234"

    @patch("noidea._run_git")
    @patch("noidea.Path.exists", return_value=True)
    def test_dirty_tree_marks_the_build(self, mock_exists, mock_git):
        from noidea import __version__, build_version

        def fake_git(repo_root, *args):
            if args[0] == "rev-parse":
                return "abc1234"
            if args[0] == "status":
                return " M noidea/provider.py"  # Uncommitted edits present.
            if args[0] == "describe":
                return f"v{__version__}"  # Even on the tag, a dirty tree is not the release.
            return None

        mock_git.side_effect = fake_git
        assert build_version() == f"{__version__}+abc1234.dirty"

    @patch("noidea._run_git", return_value=None)
    @patch("noidea.Path.exists", return_value=True)
    def test_git_unavailable_falls_back_to_plain_version(self, mock_exists, mock_git):
        # A .git dir but no usable git output (missing binary, timeout) collapses to the version.
        from noidea import __version__, build_version

        assert build_version() == __version__


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
    def test_suggest_writes_to_file(
        self, mock_diff, mock_config, mock_commit, tmp_path
    ):
        outfile = str(tmp_path / "msg.txt")
        result = runner.invoke(app, ["suggest", "--file", outfile])
        assert result.exit_code == 0
        with open(outfile) as f:
            assert f.read() == "feat: new thing"

    @patch("noidea.commands.suggest.complete", return_value="chore: big change")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["gen.txt"])
    @patch(
        "noidea.commands.suggest.load_config",
        return_value=LlmConfig(diff_chars_max=1000),
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ " + "x" * 500_000),
    )
    def test_suggest_caps_oversized_diff_before_calling_the_model(
        self, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # An oversized staged change must reach the model truncated, not whole: otherwise the
        # request blows past the context window and fails (the gemini 1M-token error).
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        user_content = mock_complete.call_args.args[1]
        # The 500 KB diff collapses to roughly the cap plus prompt scaffolding, never its full size.
        assert len(user_content) < 3000
        assert "truncated" in user_content

    @patch("noidea.commands.suggest.complete", return_value="chore: big change")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["gen.txt"])
    @patch(
        "noidea.commands.suggest.load_config",
        return_value=LlmConfig(
            diff_chars_max=0, small_model="openai/gpt-4o-mini", provider="openrouter"
        ),
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        # 500 KB: under the 600k-char routing threshold, so it stays on the small model, yet larger
        # than that model's ~350 KB window budget — so the auto cap must still bite.
        return_value=DiffResult(has_changes=True, diff="+ " + "x" * 500_000),
    )
    def test_suggest_auto_budget_truncates_to_the_small_model_window(
        self, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # With diff_chars_max=0 (auto), a diff routed to gpt-4o-mini (128k tokens) must be truncated
        # to that model's window-derived budget (~350 KB), not sent whole.
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        user_content = mock_complete.call_args.args[1]
        assert "truncated" in user_content
        assert (
            len(user_content) < 400_000
        )  # Bounded near the 128k-token budget, not 500 KB.

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

    @patch("noidea.commands.suggest.complete", return_value="fix: x")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["a.py"])
    @patch("noidea.commands.suggest.load_config", return_value=LlmConfig())
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ tiny"),
    )
    @patch("noidea.commands.suggest.get_recent_commits", return_value=[])
    def test_suggest_announces_small_model_routing(
        self, mock_log, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # A tiny diff stays on the fast/cheap model, and the routing is made visible.
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "Small diff" in result.output
        assert "claude-haiku-4-5" in result.output

    @patch("noidea.commands.suggest.complete", return_value="feat: big")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["a.py"])
    @patch(
        "noidea.commands.suggest.load_config",
        return_value=LlmConfig(context_limit=1.0),
    )
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ a substantial change"),
    )
    @patch("noidea.commands.suggest.get_recent_commits", return_value=[])
    def test_suggest_announces_escalation_routing(
        self, mock_log, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # A diff over the threshold escalates to the strong model, and that is announced.
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "escalating" in result.output
        assert "claude-sonnet-4-6" in result.output

    @patch("noidea.commands.suggest.complete", return_value="fix: thing")
    @patch("noidea.commands.suggest.get_branch_name", return_value="main")
    @patch("noidea.commands.suggest.get_staged_files", return_value=["a.py"])
    @patch("noidea.commands.suggest.load_config", return_value=LlmConfig())
    @patch(
        "noidea.commands.suggest.get_diff",
        return_value=DiffResult(has_changes=True, diff="+ change"),
    )
    @patch("noidea.commands.suggest.get_recent_commits", return_value=[])
    def test_suggest_suppresses_routing_notice_when_model_forced(
        self, mock_log, mock_diff, mock_config, mock_staged, mock_branch, mock_complete
    ):
        # --model forces a single model, so there is no routing decision to report.
        result = runner.invoke(app, ["suggest", "--model", "claude-opus-4-7"])
        assert result.exit_code == 0
        assert "Small diff" not in result.output
        assert "escalating" not in result.output


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
        with patch(
            "noidea.commands.keys.key_store.add", side_effect=KeyStoreError("locked")
        ):
            result = runner.invoke(app, ["keys", "add"], input="secret\n")
        assert "Couldn't save the key" in result.output

    def test_remove_key_keyring_error(self):
        with patch(
            "noidea.commands.keys.key_store.remove", side_effect=KeyStoreError("locked")
        ):
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
