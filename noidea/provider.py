"""Anthropic completion transport: one deep call that owns the API and its error taxonomy."""

from enum import Enum

import anthropic
from anthropic import Anthropic
from anthropic.types import TextBlock

from noidea.config import Provider
from noidea.key_store import key_store


class ErrorKind(Enum):
    """The category of a transport failure, so callers can word it without knowing anthropic."""

    AUTH = "auth"  # The API key was rejected.
    RATE_LIMIT = "rate_limit"  # Too many requests; back off and retry.
    CONNECTION = "connection"  # The API was unreachable (network/DNS/timeout).
    STATUS = "status"  # The API returned an error status, or an otherwise-unclassified failure.


class ProviderError(Exception):
    """The single failure type callers handle; anthropic's hierarchy never leaks past complete()."""

    def __init__(self, kind: ErrorKind, message: str, status_code: int | None = None):
        assert isinstance(kind, ErrorKind), "kind must be an ErrorKind"
        assert isinstance(message, str), "message must be a string"
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code


def get_api_key(provider: Provider = Provider.ANTHROPIC) -> str:
    # key_store consults the keyring first, then the ANTHROPIC_API_KEY env var for CI/headless.
    key = key_store.get(provider.value)
    if not key:
        raise SystemExit("No API key found. Run 'noidea keys add'.")
    assert isinstance(key, str) and key, "api key must be a non-empty string"
    return key


def complete(
    system: str,
    user: str,
    model: str,
    max_tokens: int,
    temperature: float = 1.0,
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

    client = Anthropic(api_key=get_api_key())
    # Translate anthropic's exception hierarchy into one ProviderError here, so no caller
    # ever imports anthropic. Specific kinds first; APIError is the catch-all base last.
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
