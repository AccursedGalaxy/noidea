import json
from unittest.mock import patch

from noidea.config import (
    deep_merge,
    initialize,
    list_keys,
    load_config,
    remove_key,
    save_key,
)


def _patch_paths(tmp_path):
    """Return a context manager patching all config paths to tmp_path."""
    return (
        patch("noidea.config.config_dir", str(tmp_path)),
        patch("noidea.config.config_path", str(tmp_path / "config.json")),
        patch("noidea.config.keys_path", str(tmp_path / "keys.json")),
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
    p1, p2, p3 = _patch_paths(tmp_path)
    with p1, p2, p3, _patch_no_repo():
        initialize()
        result = load_config()

    assert result["llm"]["max_tokens"] == 1024


def test_load_config_user_overrides_defaults(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"llm": {"max_tokens": 512}}))

    with patch("noidea.config.config_path", str(config_file)), _patch_no_repo():
        result = load_config()

    assert result["llm"]["max_tokens"] == 512
    # defaults still present for keys not overridden
    assert result["llm"]["small_model"] == "claude-haiku-4-5"


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
        patch("noidea.config.config_path", str(user_config)),
        patch("noidea.config.get_git_root", return_value=str(repo_root)),
    ):
        result = load_config()

    assert result["llm"]["max_tokens"] == 256
    assert result["llm"]["small_model"] == "claude-haiku-4-5"


def test_load_config_repo_partial_override(tmp_path):
    """Repo config only overrides system_prompt, everything else falls through."""
    repo_root = tmp_path / "repo"
    repo_noidea = repo_root / ".noidea"
    repo_noidea.mkdir(parents=True)
    repo_config = repo_noidea / "config.json"
    repo_config.write_text(json.dumps({"llm": {"system_prompt": "Custom prompt"}}))

    with (
        patch("noidea.config.config_path", str(tmp_path / "nonexistent.json")),
        patch("noidea.config.get_git_root", return_value=str(repo_root)),
    ):
        result = load_config()

    assert result["llm"]["system_prompt"] == "Custom prompt"
    assert result["llm"]["max_tokens"] == 1024
    assert result["llm"]["small_model"] == "claude-haiku-4-5"


def test_load_config_defaults_have_all_expected_keys(tmp_path):
    p1, p2, p3 = _patch_paths(tmp_path)
    with p1, p2, p3, _patch_no_repo():
        initialize()
        result = load_config()

    assert "small_model" in result["llm"]
    assert "large_model" in result["llm"]
    assert "context_limit" in result["llm"]
    assert "system_prompt" in result["llm"]
    assert "max_tokens" in result["llm"]


class TestSaveKey:
    def test_save_key_creates_new_file(self, tmp_path):
        p1, p2, p3 = _patch_paths(tmp_path)
        with p1, p2, p3:
            initialize()
            save_key("Anthropic")

        with open(tmp_path / "keys.json") as f:
            assert json.load(f) == ["Anthropic"]

    def test_save_key_appends_to_existing(self, tmp_path):
        keys_file = tmp_path / "keys.json"
        keys_file.write_text(json.dumps(["Anthropic"]))

        with patch("noidea.config.keys_path", str(keys_file)):
            save_key("OpenAI")

        with open(keys_file) as f:
            assert json.load(f) == ["Anthropic", "OpenAI"]


class TestRemoveKey:
    def test_remove_key_removes_from_list(self, tmp_path):
        keys_file = tmp_path / "keys.json"
        keys_file.write_text(json.dumps(["Anthropic", "OpenAI"]))

        with patch("noidea.config.keys_path", str(keys_file)):
            remove_key("Anthropic")

        with open(keys_file) as f:
            assert json.load(f) == ["OpenAI"]

    def test_remove_key_missing_key_does_nothing(self, tmp_path):
        p1, p2, p3 = _patch_paths(tmp_path)
        with p1, p2, p3:
            initialize()
            result = remove_key("Anthropic")  # key not in list, should not raise
        assert result is False


class TestListKeys:
    def test_list_keys_prints_keys(self, tmp_path):
        keys_file = tmp_path / "keys.json"
        keys_file.write_text(json.dumps(["Anthropic"]))

        with patch("noidea.config.keys_path", str(keys_file)):
            result = list_keys()

        assert "Anthropic" in result

    def test_list_keys_empty_after_initialize(self, tmp_path):
        p1, p2, p3 = _patch_paths(tmp_path)
        with p1, p2, p3:
            initialize()
            result = list_keys()

        assert result == []
