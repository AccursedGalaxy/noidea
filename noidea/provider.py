"""LLM completion transport: one public complete() over two backends, one error taxonomy.

Anthropic has a distinct message shape and SDK, so it gets its own transport. Every other
supported provider (OpenAI, Ollama, Gemini, DeepSeek, Groq) speaks OpenAI's chat-completions
format, so they share a single transport — one path unlocks five providers. Both transports
collapse their SDK's exception hierarchy into one ProviderError here, so callers handle a single
error type and never import a provider SDK.
"""

import re
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
_OPENAI_COMPAT = {"openai", "ollama", "gemini", "deepseek", "groq", "openrouter"}

# The default endpoint per OpenAI-compat provider; config base_url overrides any of these.
# OpenAI itself has no entry, so it falls through to the SDK's own default base URL.
_DEFAULT_BASE_URLS = {
    "ollama": "http://localhost:11434/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    # DeepSeek's base intentionally has no /v1 suffix: its API also serves the OpenAI path here.
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai/v1",
    # OpenRouter is a pure aggregator: one OpenAI-compat endpoint fronting many upstream models,
    # selected by a namespaced model name (e.g. "anthropic/claude-3.5-sonnet").
    "openrouter": "https://openrouter.ai/api/v1",
}

# Providers that need no API key (local, keyless). The OpenAI SDK still wants a non-empty key
# string, so we pass a harmless placeholder that the local backend ignores.
_NO_KEY_PROVIDERS = {"ollama"}

# OpenAI reasoning models (o-series, gpt-5) reject max_tokens and any non-default temperature;
# they require max_completion_tokens instead. This name pattern is an OpenAI-only *hint* that lets
# us map parameters up front and skip a wasted round-trip — it is not the correctness guarantee.
# The structured-error retry in _create_with_param_fallback is; see issue #29. The 'chat' exclusion
# keeps gpt-5-chat-latest (a non-reasoning endpoint) on the standard path.
_REASONING_NAME_PATTERN = re.compile(r"^(o\d|gpt-5)")

# Approximate input context window per model *family*, in tokens. Matched by substring against the
# model name (after any "provider/" prefix), first hit wins, so order most-specific first. This is
# only ever used to bound how much diff we send, so an unknown model must fall back to a value that
# is safe (small) rather than optimistic; see _DEFAULT_CONTEXT_TOKENS. Values are conservative
# floors — a family's smallest current window — because over-truncating a diff is a far cheaper
# failure than a request that overflows the window and returns nothing.
_MODEL_CONTEXT_TOKENS = (
    (
        "gemini",
        1_048_576,
    ),  # Gemini 1.5/2.x/3 flash & pro all expose at least a 1M window.
    (
        "claude",
        200_000,
    ),  # Claude's standard window; the 1M tier is opt-in beta, so assume 200k.
    ("gpt-4o", 128_000),  # gpt-4o and gpt-4o-mini.
    ("gpt-5", 200_000),
    ("deepseek", 131_072),
    ("llama", 128_000),
    ("mixtral", 32_768),
    ("mistral", 32_768),
)
# The window assumed for any model we do not recognize: a modern-but-modest floor, so an unknown
# model is bounded rather than trusted with an unbounded diff.
_DEFAULT_CONTEXT_TOKENS = 128_000


def context_window_tokens(model: str) -> int:
    """The assumed input context window, in tokens, for a model name (namespaced or bare).

    A best-effort lookup used only to size the diff we send, never a correctness guarantee: an
    unrecognized model returns the safe default floor rather than an optimistic large window.
    """
    assert isinstance(model, str) and model, "model must be a non-empty string"
    # Strip a "provider/" prefix (OpenRouter names like "google/gemini-2.5-flash") before matching.
    bare_name = model.rsplit("/", 1)[-1].lower()
    for family, tokens in _MODEL_CONTEXT_TOKENS:
        if family in bare_name:
            assert tokens > 0, "a context window must be positive"
            return tokens
    return _DEFAULT_CONTEXT_TOKENS


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
        raise TypeError(
            f"max_tokens must be a positive integer, got {type(max_tokens).__name__}"
        )
    if not isinstance(temperature, (int, float)) or temperature < 0:
        raise TypeError(
            f"temperature must be a non-negative number, got {temperature!r}"
        )
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
    assert isinstance(max_tokens, int) and max_tokens > 0, (
        "max_tokens must be a positive int"
    )
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
        raise ProviderError(
            ErrorKind.STATUS, error.message, error.status_code
        ) from error
    except anthropic.APIError as error:
        raise ProviderError(ErrorKind.STATUS, str(error)) from error
    block = message.content[0]
    # Claude can return tool_use or image blocks; we only handle text completions.
    if not isinstance(block, TextBlock):
        raise TypeError(f"Expected TextBlock, got {type(block).__name__}")
    return block.text


def _is_reasoning_model(model: str) -> bool:
    """True for an OpenAI reasoning model name (o-series or gpt-5, excluding the chat endpoint).

    A name *hint* only: the caller still gates this on provider == 'openai', and the real
    correctness guarantee is the structured-error retry, not this match. See issue #29.
    """
    assert isinstance(model, str) and model, "model must be a non-empty string"
    name = model.lower()
    result = bool(_REASONING_NAME_PATTERN.match(name)) and "chat" not in name
    assert isinstance(result, bool), "result must be a bool"
    return result


def _build_completion_kwargs(
    messages: list, model: str, max_tokens: int, temperature: float, *, reasoning: bool
) -> dict:
    """Map a completion call to a provider's parameter dialect — the one place the split lives.

    Reasoning models take max_completion_tokens and reject temperature; every other model takes
    the classic max_tokens + temperature pair. See issue #29.
    """
    assert isinstance(model, str) and model, "model must be a non-empty string"
    assert isinstance(max_tokens, int) and max_tokens > 0, (
        "max_tokens must be a positive int"
    )
    kwargs: dict = {"model": model, "messages": messages}
    if reasoning:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    assert "max_tokens" in kwargs or "max_completion_tokens" in kwargs, (
        "must request output tokens"
    )
    return kwargs


def _create_with_param_fallback(
    client,
    model: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    *,
    reasoning: bool,
):
    """Create a chat completion, collapsing openai's exception hierarchy into one ProviderError.

    A reasoning model the name hint missed rejects max_tokens with a structured 400; flip to
    reasoning params and retry once. The retry keys off the error, not the provider, so it
    self-corrects for any compat backend, not just OpenAI. See issue #29.
    """
    import openai

    assert isinstance(reasoning, bool), "reasoning must be a bool"
    assert isinstance(messages, list) and messages, "messages must be a non-empty list"
    kwargs = _build_completion_kwargs(
        messages, model, max_tokens, temperature, reasoning=reasoning
    )
    try:
        return client.chat.completions.create(**kwargs)
    except openai.AuthenticationError as error:
        raise ProviderError(ErrorKind.AUTH, str(error)) from error
    except openai.RateLimitError as error:
        raise ProviderError(ErrorKind.RATE_LIMIT, str(error)) from error
    except openai.APIConnectionError as error:
        raise ProviderError(ErrorKind.CONNECTION, str(error)) from error
    except openai.BadRequestError as error:
        # BadRequestError subclasses APIStatusError, so this clause must precede the generic one.
        # We also accept the bare param name, not just code == "unsupported_parameter", so the
        # retry survives the SDK changing or dropping the code; the cost is that an unrelated 400
        # naming these params (e.g. an out-of-range max_tokens) triggers one wasted retry that
        # then collapses to ProviderError anyway.
        unsupported = error.code == "unsupported_parameter" or error.param in (
            "max_tokens",
            "temperature",
        )
        if reasoning or not unsupported:
            raise ProviderError(
                ErrorKind.STATUS, str(error), error.status_code
            ) from error
        retry_kwargs = _build_completion_kwargs(
            messages, model, max_tokens, temperature, reasoning=True
        )
        try:
            return client.chat.completions.create(**retry_kwargs)
        except openai.OpenAIError as retry_error:
            # The reasoning-param retry also failed; collapse it rather than leak a raw SDK error.
            raise ProviderError(ErrorKind.STATUS, str(retry_error)) from retry_error
    except openai.APIStatusError as error:
        raise ProviderError(ErrorKind.STATUS, str(error), error.status_code) from error
    except openai.OpenAIError as error:
        raise ProviderError(ErrorKind.STATUS, str(error)) from error


def _extract_text(response) -> str:
    """Pull the text completion, mapping an empty or budget-starved response to a ProviderError.

    An empty completion is a provider failure, not a Python type error: callers only catch
    ProviderError, so leaking anything else would crash them with an unhandled traceback.
    """
    # A missing/empty choices list is a provider failure, not an internal invariant: aggregators
    # like OpenRouter return HTTP 200 with an error embedded in the body when an upstream model
    # fails, so the SDK never raises and we land here with no choice. Surface the embedded error
    # if present, else a generic message — always as ProviderError so callers handle it.
    if not response.choices:
        embedded_error = getattr(response, "error", None)
        detail = ""
        if isinstance(embedded_error, dict):
            detail = str(embedded_error.get("message", "")).strip()
        elif embedded_error is not None:
            detail = str(embedded_error).strip()
        message = "The provider returned no completion choices."
        if detail:
            message = f"{message} Upstream error: {detail}"
        raise ProviderError(ErrorKind.STATUS, message)
    choice = response.choices[0]
    content = choice.message.content
    assert content is None or isinstance(content, str), (
        "content must be a string or None"
    )
    if isinstance(content, str) and content:
        return content
    # A length finish with no text means the token budget was spent before any visible output —
    # typical when a reasoning model burns it all on hidden reasoning tokens — so name the fix.
    if choice.finish_reason == "length":
        raise ProviderError(
            ErrorKind.STATUS,
            "The model produced no text before exhausting its token budget. Raise llm.max_tokens"
            " — reasoning models also spend it on hidden reasoning tokens.",
        )
    raise ProviderError(ErrorKind.STATUS, "The provider returned an empty completion.")


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
    # openai is a core dependency, imported lazily so the Anthropic default path never pays
    # its import cost. A missing openai is an install fault, not a runtime error to handle.
    from openai import OpenAI

    # base_url precedence: explicit config > per-provider default > the SDK's own default (None).
    resolved_base_url = base_url or _DEFAULT_BASE_URLS.get(provider, "")
    api_key = "ollama" if provider in _NO_KEY_PROVIDERS else get_api_key(provider)
    client = OpenAI(api_key=api_key, base_url=resolved_base_url or None)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    # The name hint is an OpenAI-only optimization; the retry inside the fallback is what makes a
    # missed reasoning model still work. See issue #29.
    reasoning = provider == "openai" and _is_reasoning_model(model)
    response = _create_with_param_fallback(
        client, model, messages, max_tokens, temperature, reasoning=reasoning
    )
    return _extract_text(response)
