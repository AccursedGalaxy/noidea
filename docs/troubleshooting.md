# Troubleshooting

Each entry starts with the message or behaviour you see. Run `noidea status` first: it catches
most setup problems in one screen.

## No API key found for provider

Cause: noidea found no key for the configured provider in the keyring or in the provider's
environment variable. On `git commit` this aborts the commit.

Fix: store a key for the provider named in the message, for example `noidea keys add openai`, or
export its variable from the [providers table](providers.md). To commit right away, pass your own
message with `git commit -m`, which skips noidea.

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
part of the budget on hidden reasoning.

Fix: raise `max_tokens`, for example to `4096`:

```json
{ "llm": { "max_tokens": 4096 } }
```

## The provider returned no completion choices

Cause: the provider answered without a message. OpenRouter does this when the upstream model
fails, and noidea appends the upstream error after `Upstream error:`.

Fix: read the upstream error. If the model is unavailable, pick another one in `small_model` and
`large_model`.

## Ollama or another provider says the model does not exist

Cause: `small_model` and `large_model` still hold the default Anthropic model IDs, which other
providers do not serve.

Fix: set both to a model your provider has. For Ollama, `ollama list` shows the pulled models.

## Nothing staged yet

Cause: `noidea suggest` found no staged changes.

Fix: stage files with `git add` first. noidea only reads staged changes, never unstaged edits.

## git commit -m does not get a suggestion

Cause: this is intended. A commit that already has a message keeps it.

Fix: run `git commit` without `-m`, or run `noidea suggest` to print a suggestion.

## The editor opens without a suggestion

Cause: the hook is missing or out of date, or another tool replaced it. Hooks also stop running
when `core.hooksPath` changes after `noidea init`.

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

Cause: your user config was written with the defaults of the release you first installed, and
values in the file win over built-in defaults.

Fix: delete the key from `~/.noidea/config.json` to use the current default.
