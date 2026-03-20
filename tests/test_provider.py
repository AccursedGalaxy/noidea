import os
from unittest.mock import MagicMock, patch

import pytest

from noidea.provider import get_api_key, get_commit_message


class TestGetApiKey:
    @patch("noidea.provider.keyring")
    def test_returns_keyring_key_first(self, mock_keyring):
        mock_keyring.get_password.return_value = "kr-key-123"
        assert get_api_key() == "kr-key-123"
        mock_keyring.get_password.assert_called_once_with(
            service_name="noidea", username="anthropic"
        )

    @patch("noidea.provider.keyring")
    def test_falls_back_to_env_var(self, mock_keyring, monkeypatch):
        mock_keyring.get_password.return_value = None
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-456")
        assert get_api_key() == "env-key-456"

    @patch("noidea.provider.keyring")
    def test_exits_when_no_key_found(self, mock_keyring, monkeypatch):
        mock_keyring.get_password.return_value = None
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            get_api_key()


class TestGetCommitMessage:
    @patch("noidea.provider.get_api_key", return_value="fake-key")
    @patch("noidea.provider.Anthropic")
    def test_returns_text_from_api(self, mock_anthropic_cls, mock_get_key):
        from anthropic.types import TextBlock

        mock_block = TextBlock(type="text", text="feat: add login endpoint")

        mock_message = MagicMock()
        mock_message.content = [mock_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_cls.return_value = mock_client

        result = get_commit_message(
            diff="+ added login",
            system_prompt="generate commit msg",
            model="claude-sonnet-4-6",
            max_tokens=100,
        )

        assert result == "feat: add login endpoint"
        mock_client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-6",
            system="generate commit msg",
            messages=[{"role": "user", "content": "+ added login"}],
            max_tokens=100,
            temperature=1.0,
        )

    @patch("noidea.provider.get_api_key", return_value="fake-key")
    @patch("noidea.provider.Anthropic")
    def test_uses_api_key_from_get_api_key(self, mock_anthropic_cls, mock_get_key):
        from anthropic.types import TextBlock

        mock_block = TextBlock(type="text", text="ok")
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_cls.return_value = mock_client

        get_commit_message("diff", "prompt", "model", 10)

        mock_anthropic_cls.assert_called_once_with(api_key="fake-key")
