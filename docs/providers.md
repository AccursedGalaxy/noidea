# Providers

noidea sends each request to one provider, chosen with `llm.provider` in your
[config](configuration.md). Switching providers is a config change; nothing else needs
installing.

| `provider` | Needs a key | Key variable | Default endpoint |
|---|---|---|---|
| `anthropic` (default) | yes | `ANTHROPIC_API_KEY` | Anthropic SDK default |
| `ollama` | no | | `http://localhost:11434/v1` |
| `openai` | yes | `OPENAI_API_KEY` | OpenAI SDK default |
| `gemini` | yes | `GEMINI_API_KEY` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `deepseek` | yes | `DEEPSEEK_API_KEY` | `https://api.deepseek.com` |
| `groq` | yes | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| `openrouter` | yes | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |

## Storing keys

noidea looks for a key in two places, in this order:

1. The operating system's keyring, written by `noidea keys add <provider>`.
2. The provider's environment variable from the table above.

Use the keyring on your own machine and the environment variable on servers and in CI. If the
host has no keyring backend, noidea uses the environment variable instead of failing.
`noidea keys show` lists the providers that have a key in the keyring.

## Choosing models

Every provider uses the same two settings, `small_model` and `large_model`. Each provider comes
with its own pair, so setting `provider` alone is enough:

| Provider | `small_model` | `large_model` |
|--|--|--|
| `anthropic` | `claude-haiku-5-5` | `claude-sonnet-5-5` |
| `openai` | `gpt-6-luna` | `gpt-6.1-sol` |
| `gemini` | `gemini-3.8-flash` | `gemini-4-argon` |
| `deepseek` | `deepseek-flash` | `deepseek-v4-pro` |
| `groq` | `llama-3.1-8b-instant` | `llama-3.3-70b-versatile` |
| `openrouter` | `anthropic/claude-haiku-5.5` | `anthropic/claude-sonnet-5.5` |
| `ollama` | newest pulled model | newest pulled model |

Set either one to override it. If you only want one model, give both settings the same value.

```json
{
  "llm": {
    "provider": "openai",
    "small_model": "gpt-6-luna",
    "large_model": "gpt-6-luna"
  }
}
```

[Model routing](how-it-works.md#model-routing) explains when each one is used.

## Anthropic

The default. Run `noidea keys add` and nothing else needs configuring.

## Ollama

Ollama runs models on your own machine. noidea needs no key for it, and your diffs never leave
your computer. Install [Ollama](https://ollama.com), pull a model, then point noidea at it:

```bash
ollama pull llama3.2
```

```json
{ "llm": { "provider": "ollama" } }
```

With no model set, noidea asks Ollama for its models and uses the most recently pulled one,
skipping embedding models. Pulling another model changes the choice, so set `small_model` to pin
one; with only one of the two set, noidea uses it for both.

If Ollama listens somewhere other than `localhost:11434`, set `base_url`.

## OpenAI

```bash
noidea keys add openai
```

OpenAI's reasoning models (the `o1`, `o3` and `gpt-5` families) take `max_completion_tokens`
instead of `max_tokens` and ignore `temperature`. noidea maps these parameters for you. If any
other model rejects `max_tokens`, noidea retries once with `max_completion_tokens`.

:::{warning}
Reasoning models spend part of `max_tokens` on hidden reasoning. If the budget runs out before
any visible text, the request fails. Raise `llm.max_tokens` if that happens; see
[troubleshooting](troubleshooting.md#the-model-produced-no-text-before-exhausting-its-token-budget).
:::

## Gemini, DeepSeek and Groq

All three speak the OpenAI-compatible API at the endpoints in the table. Add a key with
`noidea keys add gemini` (or `deepseek`, `groq`). The models come from the
[table above](#choosing-models) unless you set `small_model` and `large_model`.

## OpenRouter

[OpenRouter](https://openrouter.ai) puts many upstream models behind one endpoint and one key.
Name models with their OpenRouter namespace:

```json
{
  "llm": {
    "provider": "openrouter",
    "small_model": "google/gemini-2.5-flash",
    "large_model": "anthropic/claude-sonnet-4.5"
  }
}
```

When an upstream model fails, OpenRouter can answer with an embedded error instead of a message.
noidea shows that upstream error rather than an empty suggestion.

## Self-hosted and other endpoints

`base_url` replaces the provider's default endpoint. To use any server that speaks the OpenAI
chat completions API, such as vLLM or LM Studio, set `provider` to `openai` and `base_url` to the
server:

```json
{
  "llm": {
    "provider": "openai",
    "base_url": "http://localhost:8000/v1",
    "small_model": "my-model",
    "large_model": "my-model"
  }
}
```

The key still comes from `OPENAI_API_KEY` or `noidea keys add openai`. Use a placeholder value if
the server does not check keys.
