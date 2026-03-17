# noidea

AI-powered commit message suggestions via git hooks. Stages a diff, sends it to Claude, and pre-fills your commit editor.

## Install

```bash
pip install noidea  # or: poetry install
export ANTHROPIC_API_KEY=sk-ant-...
noidea init
```

`noidea init` installs a `prepare-commit-msg` hook in your repo. From then on, every `git commit` opens your editor with a suggested message pre-filled.

## Commands

### `noidea init`
Installs the git hook. Backs up any existing `prepare-commit-msg` as `.bak`. Respects `core.hooksPath`.

### `noidea suggest`
Generates a commit message from the current staged diff and prints it.

```
Options:
  -F, --file TEXT   Write message to file instead of stdout (used by the hook)
```

## Config

Optional config at `~/.noidea/noidea.toml`:

```toml
[llm]
model = "claude-sonnet-4-6"
max_tokens = 1024
system_prompt = "Your custom prompt here"
```

Falls back to built-in defaults if no config file exists.

## Requirements

- Python 3.13+
- `ANTHROPIC_API_KEY` env var
