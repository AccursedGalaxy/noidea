# noidea

AI-powered commit message suggestions via git hooks. Stages a diff, sends it to Claude, and pre-fills your commit editor.

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
3. **`.env` file**: `ANTHROPIC_API_KEY=sk-ant-...` in a `.env` file

## Commands

### `noidea init`
Installs the `prepare-commit-msg` hook. Backs up any existing hook as `.bak`. Respects `core.hooksPath`.

### `noidea suggest`
Generates a commit message from the current staged diff and prints it.

```
Options:
  -F, --file TEXT   Write message to file instead of stdout (used by the hook)
```

### `noidea keys`

Manage API keys stored in the system keyring.

```bash
noidea keys list    # List saved keys
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

Optional config at `~/.noidea/noidea.toml`:

```toml
[llm]
model = "claude-sonnet-4-6"
max_tokens = 1024
system_prompt = "Your custom prompt here"
```

Falls back to built-in defaults if no config file exists. The default prompt follows conventional commits style (feat/fix/refactor/etc.) with a 72-character subject line limit.

## Requirements

- Python 3.13+
- Anthropic API key
