<div align="center">

# noidea

**Because you shouldn't have to think about commit messages.**

*Python-native AI commit message generator — hooks into `git commit`, learns your repo's voice, routes small diffs to cheap models. No Node.js required.*

[![PyPI](https://img.shields.io/pypi/v/noidea?style=flat-square&color=blue)](https://pypi.org/project/noidea/)
[![Downloads](https://img.shields.io/pypi/dm/noidea?style=flat-square&color=green)](https://pypi.org/project/noidea/)
[![Stars](https://img.shields.io/github/stars/AccursedGalaxy/noidea?style=flat-square)](https://github.com/AccursedGalaxy/noidea/stargazers)
[![License](https://img.shields.io/github/license/AccursedGalaxy/noidea?style=flat-square)](https://github.com/AccursedGalaxy/noidea/blob/main/LICENSE)

<br>

<img src="assets/demo.gif" alt="noidea demo" width="700">

</div>

---

## Why noidea?

Most AI commit message tools require Node.js, generate the same boilerplate every time, and run as a separate command you have to remember to call. noidea is a Python-native alternative that works differently in the ways that actually matter:

- **Writes in your repo's voice, not generic AI boilerplate.** Before generating, noidea reads how your repo already commits — its scope vocabulary, body habits, subject length, gitmoji or not — and matches it. Your history stays consistent instead of looking like a bot dropped in.
- **Spends pennies and milliseconds on trivial commits.** Small diffs go to a fast, cheap model; only substantial changes escalate to the strong one — automatically, and it tells you which it chose. No paying premium rates to commit a typo fix.
- **Never auto-commits — you always get the last word.** It pre-fills your editor on `git commit`. No new command to remember, no message committed behind your back. Edit or delete it like any draft.
- **Terminal-native and private by design.** A small, MIT-licensed Python CLI built to a strict [safety-first style guide](STYLE.md). Your diffs go straight to your chosen model and nowhere else.

### How noidea compares

|  | **noidea** | opencommit | aicommits | gptcommit |
|--|--|--|--|--|
| **Install** | `pipx install noidea` | `npm i -g opencommit` | `npm i -g aicommits` | `cargo` / `brew` |
| **Language** | Python | Node.js | Node.js | Rust |
| Hooks into `git commit` | ✅ | ✅ | ✅ | ✅ |
| Learns your repo's style | ✅ | ❌ | ❌ | ❌ |
| Cost-aware model routing | ✅ | ❌ | ❌ | ❌ |
| Multi-provider (6+) | ✅ | ✅ | ✅ | partial |
| No Node.js required | ✅ | ❌ | ❌ | ✅ |
| GitHub Action | ✅ | ❌ | ❌ | ❌ |

## Quick Start

```bash
pipx install noidea
noidea init
```

That's it. Every `git commit` now opens your editor with a suggested message pre-filled.

> Requires [pipx](https://pipx.pypa.io). Alternatively: `pip install noidea`

Works with **Claude, GPT, and local Ollama models** (plus Gemini, DeepSeek, Groq) — switching is a one-line config change, see [Multi-provider](#multi-provider). Want to try it with zero setup and no API key? Point it at a local Ollama model.

## API Key Setup

By default noidea uses Anthropic (Claude). The key is looked up in three places, in order:

| Method | Command |
|--------|---------|
| **Keyring** (recommended) | `noidea keys add` |
| **Environment variable** | `export ANTHROPIC_API_KEY=sk-ant-...` |
| **`.env` file** | `ANTHROPIC_API_KEY=sk-ant-...` in a `.env` file |

Other providers follow the same pattern with their own env var (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`) or `noidea keys add <provider>`.

**Ollama needs no key.** It runs locally, so once `provider` is set to `ollama` (below) you can generate commit messages with nothing else configured.

### Multi-provider

Set `provider` in your config (see [Config](#config)) to route every request to a different backend — no code change, no extra install:

```json
{ "llm": { "provider": "ollama" } }
```

| `provider` | Needs a key? | Default endpoint |
|------------|--------------|------------------|
| `anthropic` (default) | yes | Anthropic SDK default |
| `openai` | yes | OpenAI SDK default |
| `ollama` | **no** | `http://localhost:11434/v1` |
| `gemini` | yes | Google's OpenAI-compatible endpoint |
| `deepseek` | yes | `https://api.deepseek.com` |
| `groq` | yes | `https://api.groq.com/openai/v1` |

Set `base_url` to override the endpoint — e.g. point `openai` at a self-hosted vLLM server. Remember to also set `small_model`/`large_model` to models the provider actually serves (e.g. `"small_model": "llama3.2"` for Ollama).

> **Reasoning models:** OpenAI's reasoning models (the `o1`/`o3`/`gpt-5` family) are supported. They take `max_completion_tokens` instead of `max_tokens` and ignore `temperature`; noidea maps the parameters automatically and, for any provider, recovers if a model unexpectedly rejects `max_tokens`. Note that reasoning models spend part of the token budget on hidden reasoning, so a low `max_tokens` may leave no room for the message — raise `llm.max_tokens` if you get an empty-completion error.

## Commands

| Command | Description |
|---------|-------------|
| `noidea init` | Install the `prepare-commit-msg` hook. Backs up any existing hook. Respects `core.hooksPath`. |
| `noidea suggest` | Generate a commit message from the staged diff and print it. |
| `noidea status` | Show current config, API key status, and hook installation. |
| `noidea keys` | Manage API keys in the system keyring (`show` / `add` / `remove`). |
| `noidea test` | Send a test message to Claude to verify connectivity. |
| `noidea update` | Upgrade noidea via `pipx` (falls back to `pip`). |
| `noidea --version` | Print the current version. |

### `noidea suggest` options

```
-F, --file TEXT    Write message to file instead of stdout (used by the hook)
-M, --model TEXT   Override the model used for generation
```

## GitHub Action

noidea is also a [GitHub Action](https://github.com/marketplace/actions/noidea-ai-commit-message-suggestion). Add it to any repo and get AI-suggested commit messages posted as PR comments automatically.

```yaml
# .github/workflows/noidea-suggest.yml
name: AI commit suggestion
on: [pull_request]

jobs:
  suggest:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: AccursedGalaxy/noidea@main
        with:
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          provider: anthropic        # or openai, groq, deepseek, gemini, ollama
          post-comment: 'true'
```

Switch to a free local model with `provider: ollama` and no `api-key` — no cost, no key rotation.

## Config

Two optional config levels — both are `config.json` files:

- **User**: `~/.noidea/config.json` — applies everywhere
- **Repo**: `<repo>/.noidea/config.json` — overrides user config

Precedence: built-in defaults → user config → repo config.

```json
{
  "llm": {
    "max_tokens": 1024,
    "small_model": "claude-haiku-4-5",
    "large_model": "claude-sonnet-4-6",
    "context_limit": 600000,
    "temperature": 1.0,
    "learn_commit_style": true,
    "provider": "anthropic",
    "base_url": "",
    "system_prompt": "Your custom prompt here"
  }
}
```

Falls back to built-in defaults if no config file exists. The default prompt follows conventional commits style (`feat`/`fix`/`refactor`/etc.) with a 72-character subject line limit. Smaller diffs use `small_model` (Haiku) for speed; larger diffs automatically switch to `large_model` (Sonnet). `temperature` controls output creativity (0.0–1.0); the default of `1.0` maximises variety.

### Repo-native style learning

`learn_commit_style` (on by default) samples your recent `git log` and matches the repo's own conventions — its scope vocabulary, whether commits carry a body, typical subject length, and gitmoji usage — so suggestions read like your project's existing commits rather than generic boilerplate. It activates automatically once a repo has at least 5 commits; below that it stays out of the way. Set `"learn_commit_style": false` to disable it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines. This project follows [TigerStyle](STYLE.md) for coding standards.

## Requirements

- Python 3.10+
- An LLM provider: an Anthropic, OpenAI, Gemini, DeepSeek, or Groq API key — or a local [Ollama](https://ollama.com) install (no key needed)
