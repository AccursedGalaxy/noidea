# Troubleshooting

Each entry starts with the message or behaviour you see. Run `noidea status` first: it catches
most setup problems in one screen.

## No API key found for provider

Cause: noidea found no key for the configured provider in the keyring or in the provider's
environment variable. On `git commit` the editor opens empty and you can write the message
yourself. A `.env` file is not read; see [providers](providers.md) for the variable names.

Fix: store a key for the provider named in the message, for example `noidea keys add openai`, or
export its variable from the [providers table](providers.md). `noidea status` shows which key the
configured provider will use.

## Authentication failed. Check your API key

Cause: the provider rejected the key. It is mistyped, revoked, or belongs to another provider.

Fix: replace it with `noidea keys remove <provider>` and then `noidea keys add <provider>`. A key
in the keyring wins over an environment variable, so remove a stale keyring entry if you meant to
use the variable.

## Could not connect to the API

Cause: noidea could not reach the endpoint. With Ollama this usually means the Ollama server is
not running; elsewhere, a network problem or a wrong `base_url`.

Fix: for Ollama, start it with `ollama serve`. Otherwise check `base_url` in your
[config](configuration.md) and your connection, then run `noidea test`.

## The model produced no text before exhausting its token budget

Cause: the model used all of `max_tokens` before writing any visible text. Reasoning models spend
part of the budget on hidden reasoning. With the `anthropic` provider the message reads `The model
returned no text. Raise llm.max_tokens`.

Fix: raise `max_tokens`, for example to `16000`:

```json
{ "llm": { "max_tokens": 16000 } }
```

## The provider returned no completion choices

Cause: the provider answered without a message. OpenRouter does this when the upstream model
fails, and noidea appends the upstream error after `Upstream error:`.

Fix: read the upstream error. If the model is unavailable, pick another one in `small_model` and
`large_model`.

## Ollama or another provider says the model does not exist

Cause: `small_model` or `large_model` names a model the provider doesn't serve, for example a
Claude model ID copied into a config for another provider.

Fix: remove both settings to use the provider's own defaults, or set them to a model your provider
has. For Ollama, `ollama list` shows the pulled models.

## Ollama has no chat models installed

Cause: `small_model` and `large_model` are unset for the `ollama` provider, and the local server
lists no models other than embedding models (names containing `embed`).

Fix: run `ollama pull llama3.2`, or set `llm.small_model` and `llm.large_model`.

## The model's reply contained no commit message

Cause: after noidea removed a leading `<think>` reasoning block and any code fence wrapped around
the whole reply, nothing was left. Most often the reasoning never closed because the model ran out
of `max_tokens` while still thinking.

Fix: raise `max_tokens` so the model finishes after reasoning, or pick another model.

## Could not read the keyring

Cause: the host has no keyring backend, which is common on CI runners, containers and headless
Linux. With the provider's environment variable set, noidea uses it and `noidea status` shows
the variable. Without it, the error names the variable to set.

Fix: export the variable from the [providers table](providers.md), for example
`ANTHROPIC_API_KEY`.

## Nothing staged yet

Cause: `noidea suggest` found no staged changes.

Fix: stage files with `git add` first. noidea only reads staged changes, never unstaged edits.

## git commit -m does not get a suggestion

Cause: this is intended. A commit that already has a message keeps it.

Fix: run `git commit` without `-m`, or run `noidea suggest` to print a suggestion.

## The editor opens without a suggestion

Cause: the hook is missing or out of date, or another tool replaced it. Hooks also stop running
when `core.hooksPath` changes after `noidea init`. If the commit output says `noidea: not on PATH`,
git ran the hook without your shell's `PATH`, which GUI clients and IDEs often do.

Fix: run `noidea status`. If a hook shows as missing or `outdated`, run `noidea init`.

## noidea status shows a hook as outdated

Cause: upgrading noidea does not rewrite hooks already installed in your repositories.

Fix: run `noidea init` in each repository.

## Warning: llm.key has wrong type, using default

Cause: a value in a config file has the wrong JSON type, such as `"0.7"` (a string) for
`temperature`.

Fix: correct the type in `~/.noidea/config.json` or `.noidea/config.json`. The
[keys table](configuration.md#all-keys) lists each type.

## Warning: llm.provider is not a known provider, using default

Cause: `provider` holds a name noidea does not support, often a typo.

Fix: use one of the names in the [providers table](providers.md).

## A new release changed a default but noidea still uses the old one

Cause: the key is set in `~/.noidea/config.json` or in the repo's `.noidea/config.json`, and values
in a config file win over built-in defaults. Since 1.3.0 noidea ignores values that are exactly an
old default in the user config, so this only happens for a value someone chose.

Fix: delete the key from the config file to use the current default.
