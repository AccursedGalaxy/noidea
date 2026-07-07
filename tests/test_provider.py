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
        error = anthropic.APIConnectionError(
            request=httpx.Request("POST", "http://test")
        )
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
        error = anthropic.APIError(
            "boom", request=httpx.Request("POST", "http://test"), body=None
        )
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


class TestCompleteOpenAiCompat:
    """The shared transport for the 5 non-Anthropic providers, exercised through complete()."""

    def _mock_client(self, content: str | None = "feat: add thing"):
        # Shape a fake OpenAI client whose chat.completions.create returns one text choice.
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch("openai.OpenAI")
    def test_ollama_uses_default_base_url_and_needs_no_key(self, mock_openai_cls):
        mock_client = self._mock_client("feat: add login")
        mock_openai_cls.return_value = mock_client

        result = complete("system", "user", "llama3.2", 100, provider="ollama")

        assert result == "feat: add login"
        # No key configured: the SDK gets a harmless placeholder and the local default endpoint.
        mock_openai_cls.assert_called_once_with(
            api_key="ollama", base_url="http://localhost:11434/v1"
        )
        mock_client.chat.completions.create.assert_called_once_with(
            model="llama3.2",
            messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            max_tokens=100,
            temperature=1.0,
        )

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_openai_resolves_key_and_uses_sdk_default_endpoint(
        self, mock_openai_cls, mock_key
    ):
        mock_openai_cls.return_value = self._mock_client("hi")

        result = complete("s", "u", "gpt-4o", 50, provider="openai")

        assert result == "hi"
        # OpenAI has no per-provider default, so base_url is None (the SDK's own default).
        mock_openai_cls.assert_called_once_with(api_key="sk-test", base_url=None)
        mock_key.assert_called_once_with("openai")

    @patch("noidea.provider.get_api_key", return_value="sk-or-test")
    @patch("openai.OpenAI")
    def test_openrouter_resolves_key_and_uses_aggregator_endpoint(
        self, mock_openai_cls, mock_key
    ):
        # OpenRouter is keyed like any compat provider but fronts upstream models behind one
        # endpoint, so the model name is namespaced and the base URL is its aggregator default.
        mock_openai_cls.return_value = self._mock_client("feat: add thing")

        result = complete(
            "s", "u", "anthropic/claude-3.5-sonnet", 50, provider="openrouter"
        )

        assert result == "feat: add thing"
        mock_openai_cls.assert_called_once_with(
            api_key="sk-or-test", base_url="https://openrouter.ai/api/v1"
        )
        mock_key.assert_called_once_with("openrouter")

    @patch("openai.OpenAI")
    def test_base_url_overrides_provider_default(self, mock_openai_cls):
        mock_openai_cls.return_value = self._mock_client("ok")

        complete("s", "u", "m", 10, provider="ollama", base_url="http://vllm:8000/v1")

        mock_openai_cls.assert_called_once_with(
            api_key="ollama", base_url="http://vllm:8000/v1"
        )

    @patch("openai.OpenAI")
    def test_empty_content_raises_provider_error(self, mock_openai_cls):
        # An empty completion is a provider failure, not a Python type error: it must collapse to
        # ProviderError so callers (which only catch ProviderError) handle it gracefully instead
        # of crashing with an unhandled traceback.
        mock_openai_cls.return_value = self._mock_client(content=None)
        with pytest.raises(ProviderError) as exc:
            complete("s", "u", "m", 10, provider="ollama")
        assert exc.value.kind is ErrorKind.STATUS

    @patch("openai.OpenAI")
    def test_no_choices_with_embedded_error_raises_provider_error(
        self, mock_openai_cls
    ):
        # Aggregators (OpenRouter) return HTTP 200 with an error embedded in the body when an
        # upstream model fails: the SDK does not raise, so an empty choices list must collapse to
        # ProviderError — not an AssertionError that escapes the caller's ProviderError-only catch.
        mock_response = MagicMock()
        mock_response.choices = []
        mock_response.error = {
            "message": "The input token count exceeds the maximum allowed."
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ProviderError) as exc:
            complete("s", "u", "m", 10, provider="openrouter")

        assert exc.value.kind is ErrorKind.STATUS
        # The upstream detail is surfaced so the user sees why, not just "empty".
        assert "input token count" in exc.value.message


class TestReasoningModels:
    """OpenAI reasoning models (o-series, gpt-5) reject max_tokens and a non-default temperature;
    the compat transport must send max_completion_tokens and omit temperature for them."""

    def _response(self, content: str | None = "feat: x", finish_reason: str = "stop"):
        # A single chat-completions response carrying finish_reason, so the starvation path
        # (length-truncated, empty content) is expressible.
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = finish_reason
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response

    def _mock_client(
        self, content: str | None = "feat: x", finish_reason: str = "stop"
    ):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._response(
            content, finish_reason
        )
        return mock_client

    def _unsupported_param_error(self, param: str = "max_tokens"):
        # The structured 400 OpenAI returns when a reasoning model is sent a chat-only parameter.
        import openai

        return openai.BadRequestError(
            f"Unsupported parameter: '{param}' is not supported with this model.",
            response=httpx.Response(400, request=httpx.Request("POST", "http://test")),
            body={"code": "unsupported_parameter", "param": param},
        )

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_reasoning_model_maps_to_max_completion_tokens_and_drops_temperature(
        self, mock_openai_cls, mock_key
    ):
        mock_client = self._mock_client("feat: add thing")
        mock_openai_cls.return_value = mock_client

        # temperature=0.7 is deliberately non-default: the assertion is that we drop it, not
        # that it happens to equal the only value reasoning models accept.
        result = complete("s", "u", "o3-mini", 100, temperature=0.7, provider="openai")

        assert result == "feat: add thing"
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["max_completion_tokens"] == 100
        assert "max_tokens" not in kwargs
        assert "temperature" not in kwargs

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    @pytest.mark.parametrize("model", ["gpt-4o", "gpt-5-chat-latest"])
    def test_chat_model_keeps_max_tokens_and_temperature(
        self, mock_openai_cls, mock_key, model
    ):
        # gpt-5-chat-latest is a non-reasoning endpoint: the 'chat' exclusion must keep it here,
        # not on the reasoning path. gpt-4o is the plain regression guard.
        mock_client = self._mock_client("feat: add thing")
        mock_openai_cls.return_value = mock_client

        complete("s", "u", model, 100, temperature=0.7, provider="openai")

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["max_tokens"] == 100
        assert kwargs["temperature"] == 0.7
        assert "max_completion_tokens" not in kwargs

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_unsupported_parameter_error_retries_once_with_reasoning_params(
        self, mock_openai_cls, mock_key
    ):
        # A reasoning model the name hint misses: the first (chat-param) call is rejected with the
        # structured 400, so the transport flips to reasoning params and retries once.
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            self._unsupported_param_error("max_tokens"),
            self._response("feat: add thing"),
        ]
        mock_openai_cls.return_value = mock_client

        result = complete(
            "s", "u", "gpt-6-thinking", 100, temperature=0.7, provider="openai"
        )

        assert result == "feat: add thing"
        assert mock_client.chat.completions.create.call_count == 2
        first = mock_client.chat.completions.create.call_args_list[0].kwargs
        second = mock_client.chat.completions.create.call_args_list[1].kwargs
        assert "max_tokens" in first  # first attempt used the chat-param path
        assert second["max_completion_tokens"] == 100
        assert "max_tokens" not in second
        assert "temperature" not in second

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_retry_is_provider_agnostic(self, mock_openai_cls, mock_key):
        # The retry keys off the structured error, not the provider: a non-OpenAI compat backend
        # (here deepseek) that rejects max_tokens is recovered the same way, for free.
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            self._unsupported_param_error("max_tokens"),
            self._response("fix: thing"),
        ]
        mock_openai_cls.return_value = mock_client

        result = complete("s", "u", "deepseek-reasoner", 100, provider="deepseek")

        assert result == "fix: thing"
        assert mock_client.chat.completions.create.call_count == 2
        assert (
            "max_completion_tokens"
            in mock_client.chat.completions.create.call_args_list[1].kwargs
        )

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_retry_failure_surfaces_as_provider_error(self, mock_openai_cls, mock_key):
        # When the reasoning-param retry also fails, the SDK error must not leak: it collapses
        # into a ProviderError like every other transport failure.
        import openai

        second = openai.APIStatusError(
            "server boom",
            response=httpx.Response(503, request=httpx.Request("POST", "http://test")),
            body=None,
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            self._unsupported_param_error("max_tokens"),
            second,
        ]
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ProviderError) as exc:
            complete("s", "u", "gpt-6-thinking", 100, provider="openai")

        assert exc.value.kind is ErrorKind.STATUS
        assert mock_client.chat.completions.create.call_count == 2

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_non_param_bad_request_does_not_retry(self, mock_openai_cls, mock_key):
        # A 400 that is not an unsupported-parameter error (e.g. context length) is a genuine
        # failure: collapse to STATUS on the first call, do not retry.
        import openai

        error = openai.BadRequestError(
            "context length exceeded",
            response=httpx.Response(400, request=httpx.Request("POST", "http://test")),
            body={"code": "context_length_exceeded"},
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = error
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ProviderError) as exc:
            complete("s", "u", "gpt-4o", 100, provider="openai")

        assert exc.value.kind is ErrorKind.STATUS
        assert mock_client.chat.completions.create.call_count == 1

    @patch("noidea.provider.get_api_key", return_value="sk-test")
    @patch("openai.OpenAI")
    def test_budget_starvation_raises_actionable_provider_error(
        self, mock_openai_cls, mock_key
    ):
        # A reasoning model can spend its whole budget on hidden reasoning tokens and return empty
        # content with a length finish. Surface an actionable ProviderError naming the fix, not a
        # cryptic TypeError.
        mock_openai_cls.return_value = self._mock_client(
            content=None, finish_reason="length"
        )
        with pytest.raises(ProviderError) as exc:
            complete("s", "u", "o3-mini", 100, provider="openai")
        assert exc.value.kind is ErrorKind.STATUS
        assert "max_tokens" in str(exc.value)


class TestCompleteDispatch:
    def test_unknown_provider_is_rejected(self):
        with pytest.raises(ValueError, match="unknown provider"):
            complete("s", "u", "m", 10, provider="not-a-provider")


class TestProviderTablesStayInSync:
    """Guard against drift between the Provider enum and the routing tables. Adding a provider
    to the enum without wiring it into every table fails loudly here, not silently at runtime."""

    def _provider_values(self) -> set[str]:
        from noidea.config import Provider

        values = {member.value for member in Provider}
        assert "anthropic" in values, "anthropic must stay the default provider"
        return values

    def test_every_non_anthropic_provider_is_openai_compat(self):
        # An enum member not in _OPENAI_COMPAT would be accepted by config but raise
        # "unknown provider" inside complete(); a stray compat entry would never be reachable.
        from noidea.provider import _OPENAI_COMPAT

        assert self._provider_values() - {"anthropic"} == _OPENAI_COMPAT

    def test_default_base_urls_only_name_compat_providers(self):
        from noidea.provider import _DEFAULT_BASE_URLS, _OPENAI_COMPAT

        assert set(_DEFAULT_BASE_URLS).issubset(_OPENAI_COMPAT)

    def test_no_key_providers_are_known_providers(self):
        from noidea.provider import _NO_KEY_PROVIDERS

        assert _NO_KEY_PROVIDERS.issubset(self._provider_values())

    def test_every_key_needing_provider_has_an_env_var(self):
        # Miss an entry here and the keyring→env-var fallback silently never fires for it.
        from noidea.key_store import _PROVIDER_ENV_VARS
        from noidea.provider import _NO_KEY_PROVIDERS

        assert self._provider_values() - _NO_KEY_PROVIDERS == set(_PROVIDER_ENV_VARS)


class TestCompleteOpenAiCompatErrors:
    """complete() collapses openai's exception hierarchy into one ProviderError, like anthropic's."""

    def _complete_raising(self, error):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = error
            mock_openai_cls.return_value = mock_client
            return complete("s", "u", "m", 10, provider="ollama")

    def _response(self, status_code):
        return httpx.Response(status_code, request=httpx.Request("POST", "http://test"))

    def test_auth_error_maps_to_auth_kind(self):
        import openai

        error = openai.AuthenticationError(
            "bad key", response=self._response(401), body=None
        )
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.AUTH

    def test_rate_limit_error_maps_to_rate_limit_kind(self):
        import openai

        error = openai.RateLimitError(
            "slow down", response=self._response(429), body=None
        )
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.RATE_LIMIT

    def test_connection_error_maps_to_connection_kind(self):
        import openai

        error = openai.APIConnectionError(request=httpx.Request("POST", "http://test"))
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.CONNECTION

    def test_status_error_maps_to_status_kind_with_code(self):
        import openai

        error = openai.APIStatusError(
            "server boom", response=self._response(503), body=None
        )
        with pytest.raises(ProviderError) as exc:
            self._complete_raising(error)
        assert exc.value.kind is ErrorKind.STATUS
        assert exc.value.status_code == 503


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
