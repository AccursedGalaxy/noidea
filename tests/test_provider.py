from unittest.mock import MagicMock, patch

import anthropic
import httpx
import pytest

from noidea.provider import ErrorKind, ProviderError, complete, get_api_key


class TestGetApiKey:
    @patch("noidea.provider.key_store")
    def test_returns_key_from_store(self, mock_store):
        mock_store.get.return_value = "kr-key-123"
        assert get_api_key() == "kr-key-123"
        mock_store.get.assert_called_once_with("anthropic")

    @patch("noidea.provider.key_store")
    def test_exits_when_no_key_found(self, mock_store):
        mock_store.get.return_value = None
        with pytest.raises(SystemExit):
            get_api_key()


class TestComplete:
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

        result = complete(
            system="generate commit msg",
            user="+ added login",
            model="claude-sonnet-4-6",
            max_tokens=100,
        )

        assert result == "feat: add login endpoint"
        mock_anthropic_cls.assert_called_once_with(api_key="fake-key")
        mock_client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-6",
            system="generate commit msg",
            messages=[{"role": "user", "content": "+ added login"}],
            max_tokens=100,
            temperature=1.0,
        )


class TestCompleteErrors:
    """complete() collapses anthropic's exception hierarchy into one ProviderError."""

    def _complete_raising(self, error):
        # Drive complete() with a client whose create() raises the given anthropic error.
        with (
            patch("noidea.provider.get_api_key", return_value="fake-key"),
            patch("noidea.provider.Anthropic") as mock_anthropic_cls,
        ):
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = error
            mock_anthropic_cls.return_value = mock_client
            return complete("system", "user", "model", 100)

    def test_auth_error_maps_to_auth_kind(self):
        error = anthropic.AuthenticationError(
            message="bad key", response=MagicMock(status_code=401), body={}
        )
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.AUTH

    def test_rate_limit_error_maps_to_rate_limit_kind(self):
        error = anthropic.RateLimitError(
            message="slow down", response=MagicMock(status_code=429), body={}
        )
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.RATE_LIMIT

    def test_connection_error_maps_to_connection_kind(self):
        error = anthropic.APIConnectionError(request=httpx.Request("POST", "http://test"))
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.CONNECTION

    def test_status_error_maps_to_status_kind_with_code(self):
        error = anthropic.APIStatusError(
            "server boom", response=MagicMock(status_code=503), body={}
        )
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.STATUS
        assert exc.value.status_code == 503

    def test_unknown_api_error_falls_through_to_status_kind(self):
        # Any anthropic.APIError not matched above must still not leak past the seam.
        error = anthropic.APIError("boom", request=httpx.Request("POST", "http://test"), body=None)
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.STATUS


class TestCompleteValidation:
    """Input validation fires before any network call, so no mocking needed."""

    def test_rejects_empty_user(self):
        with pytest.raises(ValueError, match="user"):
            complete("system", "", "model", 100)

    def test_rejects_whitespace_user(self):
        with pytest.raises(ValueError, match="user"):
            complete("system", "   \n  ", "model", 100)

    def test_rejects_empty_system(self):
        with pytest.raises(ValueError, match="system"):
            complete("", "user", "model", 100)

    def test_rejects_empty_model(self):
        with pytest.raises(ValueError, match="model"):
            complete("system", "user", "", 100)

    def test_rejects_non_int_max_tokens(self):
        with pytest.raises(TypeError, match="max_tokens"):
            # The str is the point: the runtime guard must reject a non-int max_tokens.
            complete("system", "user", "model", "100")  # type: ignore[arg-type]

    def test_rejects_zero_max_tokens(self):
        with pytest.raises(TypeError, match="max_tokens"):
            complete("system", "user", "model", 0)

    def test_rejects_negative_temperature(self):
        with pytest.raises(TypeError, match="temperature"):
            complete("system", "user", "model", 100, temperature=-1)


class TestCompleteNonTextBlock:
    @patch("noidea.provider.get_api_key", return_value="fake-key")
    @patch("noidea.provider.Anthropic")
    def test_raises_on_non_text_block(self, mock_anthropic_cls, mock_get_key):
        mock_block = MagicMock()
        mock_block.__class__.__name__ = "ToolUseBlock"
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_cls.return_value = mock_client

        with pytest.raises(TypeError, match="Expected TextBlock"):
            complete("system", "user", "model", 100)
