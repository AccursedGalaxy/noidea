# noidea

AI-powered commit message suggestions via git hooks. Stages a diff, sends it to Claude, and pre-fills your commit editor.

![noidea demo](assets/demo.gif)

## Install

```bash
pipx install noidea
noidea init
```

> Requires [pipx](https://pipx.pypa.io). Alternatively: `pip install noidea`

`noidea init` installs a `prepare-commit-msg` hook in your repo. From then on, every `git commit` opens your editor with a suggested message pre-filled.

## API Key Setup

noidea needs an Anthropic API key. Three options (checked in order):

1. **Keyring** (recommended): `noidea keys add`
2. **Environment variable**: `export ANTHROPIC_API_KEY=sk-ant-...`
3. **`.env` file**: `ANTHROPIC_API_KEY=sk-ant-...` in a `.env` file (used for development)

## Commands

### `noidea init`
Installs the `prepare-commit-msg` hook. Backs up any existing hook as `.bak`. Respects `core.hooksPath`.

### `noidea suggest`
Generates a commit message from the current staged diff and prints it.

```
Options:
  -F, --file TEXT    Write message to file instead of stdout (used by the hook)
  -M, --model TEXT   Override the model used for generation
```

### `noidea status`
Shows the current noidea configuration, API key status, and whether the git hook is installed.

### `noidea keys`

Manage API keys stored in the system keyring.

```bash
noidea keys show    # Show saved keys
noidea keys add     # Add a key interactively
noidea keys remove  # Remove a key interactively
```

### `noidea test`
Sends a test message to the Claude API to verify your key and connectivity work.

### `noidea update`
Updates noidea via `pipx upgrade noidea` (falls back to `pip install --upgrade noidea`).

### `noidea --version`
Prints the current version.

## Config

noidea supports two levels of configuration, both optional:

- **User config**: `~/.noidea/config.json` — applies to all repositories
- **Repository config**: `<repo>/.noidea/config.json` — overrides user config for a specific repo

Precedence: built-in defaults → user config → repository config.

```json
{
  "llm": {
    "max_tokens": 1024,
    "small_model": "claude-haiku-4-5",
    "large_model": "claude-sonnet-4-6",
    "context_limit": 600000,
    "system_prompt": "Your custom prompt here"
  }
}
```

Falls back to built-in defaults if no config file exists. The default prompt follows conventional commits style (feat/fix/refactor/etc.) with a 72-character subject line limit. Smaller diffs use `small_model` (Haiku) for speed; larger diffs automatically switch to `large_model` (Sonnet).

## Requirements

- Python 3.10+
- Anthropic API key
