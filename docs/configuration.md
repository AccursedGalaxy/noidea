# Configuration

Every setting lives under the `llm` key of a JSON config file, and every one has a default, so a
config file only needs the keys you want to change.

## Where config lives

noidea reads up to two files and merges them over its built-in defaults. A later layer wins:

1. Built-in defaults.
2. User config, `~/.noidea/config.json`, for every repository on your machine.
3. Repo config, `<repo>/.noidea/config.json`, for one repository. Commit it to share settings
   with your team.

The first `noidea` command you ever run creates `~/.noidea/config.json` with an empty `llm`
section. Add only the keys you want to change; everything else follows the built-in defaults,
including new defaults in later releases.

Releases before 1.3.0 wrote every default into that file. noidea now ignores a value there when it
is exactly an old default (for example `"small_model": "claude-haiku-4-5"` or the old built-in
system prompt), so those files pick up current defaults too. Values in a repo config are always
used as written.

`noidea status` prints the models, context limit and temperature currently in effect.

A value of the wrong type is ignored with a warning, and the default is used instead:

```text
Warning: llm.temperature has wrong type (str), using default.
```

## All keys

| Key | Type | Default | Effect |
|---|---|---|---|
| `provider` | string | `"anthropic"` | Which [provider](providers.md) receives requests. |
| `small_model` | string | `"claude-haiku-5-5"` | Model for ordinary diffs. |
| `large_model` | string | `"claude-sonnet-5-5"` | Model for diffs at or over `context_limit`, and for `noidea test`. |
| `context_limit` | number | `40000` | Size in characters where routing switches to `large_model`. |
| `diff_chars_max` | integer | `0` | Upper limit on diff characters sent. `0` sizes it from the model's context window. |
| `max_tokens` | integer | `8192` | Output token budget per request. Current Claude models spend part of it thinking before they answer. |
| `temperature` | number | `1.0` | Sampling temperature. Lower values give more predictable wording. Current Claude models (the 5.5 generation) only accept `1.0`. |
| `learn_commit_style` | boolean | `true` | Match the repo's own commit conventions. |
| `system_prompt` | string | built in | The instructions sent with every diff. |
| `base_url` | string | `""` | Replaces the provider's default endpoint. |
| `use_agent` | boolean | `false` | Experimental. Use the agent backend by default. |
| `agent_binary` | string | `""` | Experimental. Path to the agent binary. |
| `agent_model` | string | `"google/gemini-3-flash-preview"` | Experimental. OpenRouter model the agent runs on. |
| `agent_proposal_ttl_seconds` | integer | `3600` | Experimental. How long a queued agent message stays usable. |

## Model routing

`context_limit` and the two model keys decide which model writes each message. With the defaults,
a change of up to about 40,000 characters (roughly a 1,000-line diff) goes to the small model and
anything larger to the large one. Raise `context_limit` to use the large model less often, or lower
it to use it more. The rule is in
[how it works](how-it-works.md#model-routing).

For a one-off override, `noidea suggest --model <name>` uses that model regardless of size.

## Large diffs

A commit of generated files can be bigger than any model's context window. noidea trims the diff
to fit the model that will receive it and keeps the complete list of changed file names, so the
message can still mention every file. Set `diff_chars_max` to trim earlier, which bounds cost and
latency on huge commits:

```json
{ "llm": { "diff_chars_max": 100000 } }
```

## Style learning

With `learn_commit_style` on, noidea adapts each suggestion to the repo's recent commits. It
needs at least 5 commits and stays inactive below that. Turn it off to get the plain default
format everywhere:

```json
{ "llm": { "learn_commit_style": false } }
```

[Style learning](how-it-works.md#style-learning) lists what it picks up.

## The system prompt

The built-in prompt asks for a Conventional Commits subject (`feat(scope): ...`) in the
imperative mood, at most 72 characters and with no trailing period. A body is added only when the
reason or scope is not obvious, as one bullet per change. Replace it with `system_prompt`:

```json
{
  "llm": {
    "system_prompt": "Write a one-line commit subject in plain English. Output only the subject."
  }
}
```

Style learning still sends the repo's conventions along with each diff. Turn it off as well if
your prompt should be the only instruction.

## Experimental: agent backend

The agent backend is an alternative generator that works over several steps, reading the
repo's conventions and the changed files before writing a message. It is slower and
experimental, and it needs the separate driver-os `commit-msg` binary plus an OpenRouter key.

- Turn it on per run with `noidea suggest --agent`, or for every commit with `use_agent`.
- noidea finds the binary at `agent_binary`, then `$NOIDEA_AGENT_BIN`, then
  `driver-os-commit-msg` on your `PATH`.
- If the binary is missing, fails, or runs for more than 120 seconds, noidea falls back to the
  normal single request. A commit is never blocked by the agent.
- A message from `noidea suggest --agent` is queued. The next `git commit` with the same staged
  files on the same branch uses it, as long as that happens within
  `agent_proposal_ttl_seconds`.

After the commit, the `post-commit` hook records whether you kept, edited or replaced the agent's
message. These records stay on your machine; see
[files noidea writes](how-it-works.md#files-noidea-writes).
