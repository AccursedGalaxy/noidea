"""LLM completion transport: one public complete() over two backends, one error taxonomy.

Anthropic has a distinct message shape and SDK, so it gets its own transport. Every other
supported provider (OpenAI, Ollama, Gemini, DeepSeek, Groq) speaks OpenAI's chat-completions
format, so they share a single transport — one path unlocks five providers. Both transports
collapse their SDK's exception hierarchy into one ProviderError here, so callers handle a single
error type and never import a provider SDK.
"""

from enum import Enum

import anthropic
from anthropic import Anthropic
from anthropic.types import TextBlock

from noidea.key_store import key_store


class ErrorKind(Enum):
    """The category of a transport failure, so callers can word it without knowing the SDK."""

    AUTH = "auth"  # The API key was rejected.
    RATE_LIMIT = "rate_limit"  # Too many requests; back off and retry.
    CONNECTION = "connection"  # The API was unreachable (network/DNS/timeout).
    STATUS = "status"  # The API returned an error status, or an otherwise-unclassified failure.


class ProviderError(Exception):
    """The single failure type callers handle; an SDK's hierarchy never leaks past complete()."""

    def __init__(self, kind: ErrorKind, message: str, status_code: int | None = None):
        assert isinstance(kind, ErrorKind), "kind must be an ErrorKind"
        assert isinstance(message, str), "message must be a string"
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code


# Providers that speak OpenAI's chat-completions format, served by the one shared transport.
_OPENAI_COMPAT = {"openai", "ollama", "gemini", "deepseek", "groq"}

# The default endpoint per OpenAI-compat provider; config base_url overrides any of these.
# OpenAI itself has no entry, so it falls through to the SDK's own default base URL.
_DEFAULT_BASE_URLS = {
    "ollama": "http://localhost:11434/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    # DeepSeek's base intentionally has no /v1 suffix: its API also serves the OpenAI path here.
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai/v1",
}

# Providers that need no API key (local, keyless). The OpenAI SDK still wants a non-empty key
# string, so we pass a harmless placeholder that the local backend ignores.
_NO_KEY_PROVIDERS = {"ollama"}


def get_api_key(provider: str = "anthropic") -> str:
    # key_store consults the keyring first, then the provider's *_API_KEY env var for CI/headless.
    assert isinstance(provider, str) and provider, "provider must be a non-empty string"
    key = key_store.get(provider)
    if not key:
        raise SystemExit(f"No API key found for {provider}. Run 'noidea keys add'.")
    assert isinstance(key, str) and key, "api key must be a non-empty string"
    return key


def complete(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    temperature: float = 1.0,
    *,
    provider: str = "anthropic",
    base_url: str = "",
) -> str:
    # Validate inputs at the API boundary before spending a network round-trip.
    if not isinstance(system, str) or not system.strip():
        raise ValueError("system must be a non-empty string")
    if not isinstance(user, str) or not user.strip():
        raise ValueError("user must be a non-empty string")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise TypeError(f"max_tokens must be a positive integer, got {type(max_tokens).__name__}")
    if not isinstance(temperature, (int, float)) or temperature < 0:
        raise TypeError(f"temperature must be a non-negative number, got {temperature!r}")
    assert isinstance(provider, str) and provider, "provider must be a non-empty string"
    assert isinstance(base_url, str), "base_url must be a string"

    # Dispatch on provider: Anthropic's own transport, else the shared OpenAI-compat one.
    if provider == "anthropic":
        return _complete_anthropic(system, user, model, max_tokens, temperature)
    if provider in _OPENAI_COMPAT:
        return _complete_openai_compat(
            system, user, model, max_tokens, temperature, provider, base_url
        )
    raise ValueError(f"unknown provider: {provider!r}")


def _complete_anthropic(
    system: str, user: str, model: str, max_tokens: int, temperature: float
) -> str:
    """Anthropic transport: build a client, translate its errors to one ProviderError."""
    assert isinstance(model, str) and model, "model must be a non-empty string"
    assert isinstance(max_tokens, int) and max_tokens > 0, "max_tokens must be a positive int"
    client = Anthropic(api_key=get_api_key())
    # Specific kinds first; APIError is the catch-all base last.
    try:
        message = client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except anthropic.AuthenticationError as error:
        raise ProviderError(ErrorKind.AUTH, error.message) from error
    except anthropic.RateLimitError as error:
        raise ProviderError(ErrorKind.RATE_LIMIT, error.message) from error
    except anthropic.APIConnectionError as error:
        raise ProviderError(ErrorKind.CONNECTION, str(error)) from error
    except anthropic.APIStatusError as error:
        raise ProviderError(ErrorKind.STATUS, error.message, error.status_code) from error
    except anthropic.APIError as error:
        raise ProviderError(ErrorKind.STATUS, str(error)) from error
    block = message.content[0]
    # Claude can return tool_use or image blocks; we only handle text completions.
    if not isinstance(block, TextBlock):
        raise TypeError(f"Expected TextBlock, got {type(block).__name__}")
    return block.text


def _complete_openai_compat(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    temperature: float,
    provider: str,
    base_url: str,
) -> str:
    """Shared transport for the OpenAI-compatible providers; one error ladder serves all of them."""
    assert provider in _OPENAI_COMPAT, "provider must be an OpenAI-compatible provider"
    assert isinstance(base_url, str), "base_url must be a string"
    try:
        import openai
        from openai import OpenAI
    except ImportError as error:
        raise ProviderError(
            ErrorKind.STATUS,
            "The 'openai' package is required for this provider. Run 'pip install openai'.",
        ) from error
    # base_url precedence: explicit config > per-provider default > the SDK's own default (None).
    resolved_base_url = base_url or _DEFAULT_BASE_URLS.get(provider, "")
    api_key = "ollama" if provider in _NO_KEY_PROVIDERS else get_api_key(provider)
    client = OpenAI(api_key=api_key, base_url=resolved_base_url or None)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except openai.AuthenticationError as error:
        raise ProviderError(ErrorKind.AUTH, str(error)) from error
    except openai.RateLimitError as error:
        raise ProviderError(ErrorKind.RATE_LIMIT, str(error)) from error
    except openai.APIConnectionError as error:
        raise ProviderError(ErrorKind.CONNECTION, str(error)) from error
    except openai.APIStatusError as error:
        raise ProviderError(ErrorKind.STATUS, str(error), error.status_code) from error
    except openai.OpenAIError as error:
        raise ProviderError(ErrorKind.STATUS, str(error)) from error
    content = response.choices[0].message.content
    # A compat backend can return None or a non-string when no text was produced.
    if not isinstance(content, str) or not content:
        raise TypeError(f"Expected a text completion, got {type(content).__name__}")
    return content
