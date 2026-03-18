import json
from unittest.mock import patch

from noidea.config import list_keys, load_config, remove_key, save_key


def test_load_config_file_does_not_exist(tmp_path):
    fake_path = str(tmp_path / "config.json")

    with patch("noidea.config.config_path", fake_path):
        result = load_config()

    assert result["llm"]["max_tokens"] == 1024


def test_load_config_file_exists(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"llm": {"max_tokens": 512}}))

    with patch("noidea.config.config_path", str(config_file)):
        result = load_config()

    assert result["llm"]["max_tokens"] == 512


def test_load_config_defaults_have_all_expected_keys(tmp_path):
    fake_path = str(tmp_path / "config.json")
    with patch("noidea.config.config_path", fake_path):
        result = load_config()

    assert "model" in result["llm"]
    assert "system_prompt" in result["llm"]
    assert "max_tokens" in result["llm"]


class TestSaveKey:
    def test_save_key_creates_new_file(self, tmp_path):
        keys_file = str(tmp_path / "keys.json")
        with patch("noidea.config.keys_path", keys_file):
            save_key("Anthropic")

        with open(keys_file) as f:
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

    def test_remove_key_no_file_does_nothing(self, tmp_path):
        fake_path = str(tmp_path / "keys.json")
        with patch("noidea.config.keys_path", fake_path):
            remove_key("Anthropic")  # should not raise


class TestListKeys:
    def test_list_keys_prints_keys(self, tmp_path):
        keys_file = tmp_path / "keys.json"
        keys_file.write_text(json.dumps(["Anthropic"]))

        with patch("noidea.config.keys_path", str(keys_file)):
            result = list_keys()

        assert "Anthropic" in result

    def test_list_keys_no_file(self, tmp_path):
        fake_path = str(tmp_path / "keys.json")
        with patch("noidea.config.keys_path", fake_path):
            result = list_keys()

        assert result == []
