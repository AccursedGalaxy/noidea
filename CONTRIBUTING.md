# Contributing to noidea

Thanks for your interest in contributing to **noidea**! We welcome bug reports, feature requests, and pull requests. For large or non-trivial changes, please open an issue first so we can discuss the approach.

## Prerequisites

- **Python 3.10+**
- **Poetry** ([installation guide](https://python-poetry.org/docs/#installation))
- **Git**
- **An API key for any supported provider**, or a local Ollama install, only if you want to try
  noidea against a real model. The test suite needs neither.

## Development Setup

```bash
git clone https://github.com/AccursedGalaxy/noidea.git
cd noidea
poetry install
poetry run noidea --version  # verify the install
```

## API Key for Development

noidea looks up a provider's key in this order:

1. The system keyring, written by `poetry run noidea keys add <provider>`.
2. The provider's environment variable, such as `ANTHROPIC_API_KEY`.

In a development checkout, a `.env` file in the project root also works, because `key_store.py`
loads the nearest `.env` above the package. That lookup starts from the package directory, so it
does not find a `.env` in other repositories once noidea is installed.

Tests mock every API call, so `poetry run pytest` needs no key.

## Running Tests

```bash
poetry run pytest
```

CI runs the test suite on Python 3.10, 3.11, 3.12, and 3.13. All checks must pass before a PR can be merged.

## Code Style

This project follows **[TigerStyle](STYLE.md)**. Read it before writing code. The style prioritizes safety, performance, and developer experience.

### Tooling

We use **isort** + **black** for formatting and **pyright** for type checking. All three are included as dev dependencies (`poetry install` pulls them in).

**Format the entire project:**

```bash
poetry run isort .
poetry run black .
```

**Type check:**

```bash
poetry run pyright
```

### Key Style Rules

- **Assertions:** assert function arguments, return values, and invariants. Aim for at least two assertions per function.
- **Naming:** use `snake_case`, do not abbreviate, add units/qualifiers last (e.g. `latency_ms_max`).
- **Function length:** hard limit of 70 lines per function.
- **Line length:** hard limit of 100 columns.
- **Comments:** always explain *why*, not just *what*. Comments are full sentences with proper punctuation.
- **Error handling:** handle all errors explicitly, and never silently ignore failures.
- **Control flow:** keep it simple and explicit. Centralize branching logic; keep leaf functions pure.
- Use type hints for function signatures.
- Use [`rich`](https://github.com/Textualize/rich) for all user-facing stderr output.

See [STYLE.md](STYLE.md) for the full guide.

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description
```

**Types:** `feat`, `fix`, `refactor`, `chore`, `ci`, `docs`, `test`

**Scopes** (optional but encouraged): `cli`, `config`, `git`, `provider`

**Rules:**
- Use imperative mood (`add`, not `added` or `adds`)
- Keep the subject line to 72 characters or less
- No trailing period

**Examples from this repo:**
```
feat(config): clarify conventional commits format in system prompt
feat(status): add status command to show noidea configuration and hook status
refactor: improve CLI app configuration and main callback
```

## Project Architecture

| Module | Description |
|---|---|
| `cli.py` | Typer app entry point: registers commands and the `--version` flag |
| `commands/` | One module per CLI command: `init`, `keys`, `status`, `suggest`, `test`, `update`, `uninstall`, plus the hidden `_reconcile` |
| `config.py` | `LlmConfig` and 3-tier config loading: defaults → user (`~/.noidea/config.json`) → repo (`.noidea/config.json`) |
| `git.py` | Git subprocess wrappers and the hook scripts `noidea init` installs |
| `provider.py` | `complete()`: one transport for every provider, with a single `ProviderError` type |
| `key_store.py` | API keys: the OS keyring plus the `keys.json` name registry, kept in sync |
| `style.py` | Style learning: turns recent commits into prompt hints |
| `agent_backend.py`, `dogfood.py` | The experimental agent backend and its proposal queue |

> **Config note:** Configuration merges three layers (defaults, user-level, repo-level) with later layers overriding earlier ones. Keep this in mind when touching config code.

## Pull Request Workflow

1. Open an issue first for non-trivial changes, so we can agree on the approach.
2. Fork and branch from `main` (for example `feat/add-mistral-provider`).
3. Make your changes and add tests for new behaviour.
4. Run `poetry run pytest`.
5. Add a line to `CHANGELOG.md` under `[Unreleased]`, in [Keep a Changelog](https://keepachangelog.com/) format.
6. Update the docs in `docs/` if users will notice the change. `docs/CONVENTION.md` says which page owns which fact.
7. Open a PR against `main`.

## Documentation

The user docs in `docs/` are a Sphinx site written in Markdown (MyST) and published to
[noidea.readthedocs.io](https://noidea.readthedocs.io). To build it locally:

```bash
python -m venv .docs-venv
.docs-venv/bin/pip install -r docs/requirements.txt
.docs-venv/bin/sphinx-build -W -b html docs docs/_build/html
```

`notes/` holds design notes from past features. They are history, not documentation.

## Releases

Releases are triggered by pushing a `v*` tag (e.g., `v0.6.0`). CI builds the package and publishes to PyPI via trusted publishing.
