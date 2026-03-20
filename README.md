<div align="center">

# noidea

**Because you shouldn't have to think about commit messages.**

Stages your diff, sends it to an AI, and pre-fills your commit editor — so you never have to write a commit message again.

[![PyPI](https://img.shields.io/pypi/v/noidea?style=flat-square&color=blue)](https://pypi.org/project/noidea/)
[![Downloads](https://img.shields.io/pypi/dm/noidea?style=flat-square&color=green)](https://pypi.org/project/noidea/)
[![Stars](https://img.shields.io/github/stars/AccursedGalaxy/noidea?style=flat-square)](https://github.com/AccursedGalaxy/noidea/stargazers)
[![License](https://img.shields.io/github/license/AccursedGalaxy/noidea?style=flat-square)](https://github.com/AccursedGalaxy/noidea/blob/main/LICENSE)

<br>

<img src="assets/demo.gif" alt="noidea demo" width="700">

</div>

---

## Quick Start

```bash
pipx install noidea
noidea init
```

That's it. Every `git commit` now opens your editor with a suggested message pre-filled.

> Requires [pipx](https://pipx.pypa.io). Alternatively: `pip install noidea`

## API Key Setup

noidea needs an Anthropic API key. Three options (checked in order):

| Method | Command |
|--------|---------|
| **Keyring** (recommended) | `noidea keys add` |
| **Environment variable** | `export ANTHROPIC_API_KEY=sk-ant-...` |
| **`.env` file** | `ANTHROPIC_API_KEY=sk-ant-...` in a `.env` file |

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
    "system_prompt": "Your custom prompt here"
  }
}
```

Falls back to built-in defaults if no config file exists. The default prompt follows conventional commits style (`feat`/`fix`/`refactor`/etc.) with a 72-character subject line limit. Smaller diffs use `small_model` (Haiku) for speed; larger diffs automatically switch to `large_model` (Sonnet). `temperature` controls output creativity (0.0–1.0); the default of `1.0` maximises variety.

## Requirements

- Python 3.10+
- Anthropic API key
