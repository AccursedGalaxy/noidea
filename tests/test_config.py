import json
from unittest.mock import patch

from noidea.config import (
    LlmConfig,
    deep_merge,
    initialize,
    load_config,
)


class TestLlmConfig:
    def test_defaults_match_known_values(self):
        cfg = LlmConfig()
        assert cfg.max_tokens == 1024
        assert cfg.small_model == "claude-haiku-4-5"

    def test_from_dict_keeps_valid_value(self):
        cfg = LlmConfig.from_dict({"max_tokens": 512})
        assert cfg.max_tokens == 512
        # Untouched fields fall back to defaults.
        assert cfg.small_model == "claude-haiku-4-5"

    def test_from_dict_wrong_type_falls_back_to_default(self, capsys):
        cfg = LlmConfig.from_dict({"max_tokens": "not a number"})
        assert cfg.max_tokens == 1024
        assert "Warning" in capsys.readouterr().err

    def test_from_dict_missing_key_uses_default(self):
        cfg = LlmConfig.from_dict({})
        assert cfg.temperature == 1.0

    def test_from_dict_accepts_float_context_limit(self):
        cfg = LlmConfig.from_dict({"context_limit": 500000.0})
        assert cfg.context_limit == 500000.0

    def test_from_dict_rejects_float_max_tokens(self, capsys):
        # max_tokens is int-only (the API wants an int); a float falls back with a warning.
        cfg = LlmConfig.from_dict({"max_tokens": 512.5})
        assert cfg.max_tokens == 1024
        assert "Warning" in capsys.readouterr().err

    def test_from_dict_rejects_bool_for_numeric(self):
        # bool is an int subclass but is never a valid numeric config value.
        cfg = LlmConfig.from_dict({"max_tokens": True})
        assert cfg.max_tokens == 1024

    def test_select_model_small_below_limit(self):
        cfg = LlmConfig(context_limit=100)
        assert cfg.select_model(50) == cfg.small_model

    def test_select_model_large_at_limit(self):
        cfg = LlmConfig(context_limit=100)
        assert cfg.select_model(100) == cfg.large_model


def _patch_paths(tmp_path):
    """Return a context manager patching all config paths to tmp_path."""
    return (
        patch("noidea.config.CONFIG_DIR", str(tmp_path)),
        patch("noidea.config.CONFIG_PATH", str(tmp_path / "config.json")),
    )


def _patch_no_repo():
    """Patch get_git_root to return empty string (not in a repo)."""
    return patch("noidea.config.get_git_root", return_value="")


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        assert deep_merge(base, override) == {"a": 1, "b": 3}

    def test_nested_override(self):
        base = {"llm": {"model": "haiku", "max_tokens": 1024}}
        override = {"llm": {"model": "sonnet"}}
        result = deep_merge(base, override)
        assert result == {"llm": {"model": "sonnet", "max_tokens": 1024}}

    def test_new_key_added(self):
        base = {"a": 1}
        override = {"b": 2}
        assert deep_merge(base, override) == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self):
        base = {"a": 1}
        override = {"a": 2}
        deep_merge(base, override)
        assert base == {"a": 1}

    def test_empty_override(self):
        base = {"a": 1}
        assert deep_merge(base, {}) == {"a": 1}


def test_load_config_returns_defaults_after_initialize(tmp_path):
    p1, p2 = _patch_paths(tmp_path)
    with p1, p2, _patch_no_repo():
        initialize()
        result = load_config()

    assert result.max_tokens == 1024


def test_load_config_user_overrides_defaults(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"llm": {"max_tokens": 512}}))

    with patch("noidea.config.CONFIG_PATH", str(config_file)), _patch_no_repo():
        result = load_config()

    assert result.max_tokens == 512
    # defaults still present for keys not overridden
    assert result.small_model == "claude-haiku-4-5"


def test_load_config_repo_overrides_user(tmp_path):
    # user config
    user_config = tmp_path / "user_config.json"
    user_config.write_text(json.dumps({"llm": {"max_tokens": 512}}))

    # repo config
    repo_root = tmp_path / "repo"
    repo_noidea = repo_root / ".noidea"
    repo_noidea.mkdir(parents=True)
    repo_config = repo_noidea / "config.json"
    repo_config.write_text(json.dumps({"llm": {"max_tokens": 256}}))

    with (
        patch("noidea.config.CONFIG_PATH", str(user_config)),
        patch("noidea.config.get_git_root", return_value=str(repo_root)),
    ):
        result = load_config()

    assert result.max_tokens == 256
    assert result.small_model == "claude-haiku-4-5"


def test_load_config_repo_partial_override(tmp_path):
    """Repo config only overrides system_prompt, everything else falls through."""
    repo_root = tmp_path / "repo"
    repo_noidea = repo_root / ".noidea"
    repo_noidea.mkdir(parents=True)
    repo_config = repo_noidea / "config.json"
    repo_config.write_text(json.dumps({"llm": {"system_prompt": "Custom prompt"}}))

    with (
        patch("noidea.config.CONFIG_PATH", str(tmp_path / "nonexistent.json")),
        patch("noidea.config.get_git_root", return_value=str(repo_root)),
    ):
        result = load_config()

    assert result.system_prompt == "Custom prompt"
    assert result.max_tokens == 1024
    assert result.small_model == "claude-haiku-4-5"


def test_load_config_non_dict_llm_falls_back_to_defaults(tmp_path):
    """A corrupt non-dict llm section yields an all-default config, not a crash."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"llm": "broken"}))

    with patch("noidea.config.CONFIG_PATH", str(config_file)), _patch_no_repo():
        result = load_config()

    assert result.max_tokens == 1024
    assert result.small_model == "claude-haiku-4-5"


class TestLoadConfigErrors:
    def test_corrupted_json_falls_back_to_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("{not valid json!!!")

        with patch("noidea.config.CONFIG_PATH", str(config_file)), _patch_no_repo():
            result = load_config()

        assert result.max_tokens == 1024

    def test_unreadable_config_falls_back_to_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"llm": {"max_tokens": 512}}))
        config_file.chmod(0o000)

        try:
            with patch("noidea.config.CONFIG_PATH", str(config_file)), _patch_no_repo():
                result = load_config()
            assert result.max_tokens == 1024
        finally:
            config_file.chmod(0o644)

    def test_corrupted_repo_config_uses_user_config(self, tmp_path):
        user_config = tmp_path / "config.json"
        user_config.write_text(json.dumps({"llm": {"max_tokens": 512}}))

        repo_root = tmp_path / "repo"
        repo_noidea = repo_root / ".noidea"
        repo_noidea.mkdir(parents=True)
        repo_config = repo_noidea / "config.json"
        repo_config.write_text("{broken json")

        with (
            patch("noidea.config.CONFIG_PATH", str(user_config)),
            patch("noidea.config.get_git_root", return_value=str(repo_root)),
        ):
            result = load_config()

        assert result.max_tokens == 512


class TestInitializeErrors:
    def test_makedirs_failure_prints_warning(self, tmp_path, capsys):
        with (
            patch("noidea.config.CONFIG_DIR", str(tmp_path / "no" / "way")),
            patch("noidea.config.os.makedirs", side_effect=OSError("Permission denied")),
            patch("noidea.config.CONFIG_PATH", str(tmp_path / "config.json")),
        ):
            initialize()

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Permission denied" in captured.err

    def test_config_write_failure_prints_warning(self, tmp_path, capsys):
        p1, p2 = _patch_paths(tmp_path)
        with p1, p2:
            # Create dir but make config write fail.
            with patch("builtins.open", side_effect=OSError("Disk full")):
                initialize()

        captured = capsys.readouterr()
        assert "Warning" in captured.err
