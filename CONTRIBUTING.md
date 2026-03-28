# Contributing to noidea

Thanks for your interest in contributing to **noidea**! We welcome bug reports, feature requests, and pull requests. For large or non-trivial changes, please open an issue first so we can discuss the approach.

## Prerequisites

- **Python 3.10+**
- **Poetry** ([installation guide](https://python-poetry.org/docs/#installation))
- **Git**
- **Anthropic API key** — only needed for manual testing against the real API, *not* for running the test suite

## Development Setup

```bash
git clone https://github.com/AccursedGalaxy/noidea.git
cd noidea
poetry install
poetry run noidea --version  # verify the install
```

## API Key for Development

noidea resolves your Anthropic API key in this order:

1. **System keyring** — `keyring set noidea anthropic_api_key`
2. **Environment variable** — `export ANTHROPIC_API_KEY=sk-ant-...`
3. **`.env` file** — create a `.env` in the project root with `ANTHROPIC_API_KEY=sk-ant-...`

> **Note:** Tests mock all API calls, so you do **not** need a key to run `pytest`. A key is only required if you want to manually test against the real Anthropic API.

## Running Tests

```bash
poetry run pytest
```

CI runs the test suite on Python 3.10, 3.11, 3.12, and 3.13. All checks must pass before a PR can be merged.

## Code Style

This project follows **[TigerStyle](STYLE.md)** — read it before writing code. The style prioritizes safety, performance, and developer experience.

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
- **Error handling:** handle all errors explicitly — never silently ignore failures.
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
| `cli.py` | Typer app entry point — registers commands and the `--version` flag |
| `commands/` | One module per CLI command: `init`, `keys`, `status`, `suggest`, `test`, `update` |
| `config.py` | 3-tier config loading: defaults → user (`~/.noidea/config.json`) → repo (`.noidea/config.json`) |
| `git.py` | Git subprocess wrappers (diff, log, branch, staged files, etc.) |
| `provider.py` | Anthropic API client for generating commit messages |

> **Config note:** Configuration merges three layers (defaults, user-level, repo-level) with later layers overriding earlier ones. Keep this in mind when touching config code.

## Pull Request Workflow

1. **Open an issue** or discuss first for non-trivial changes
2. **Fork & branch** from `main` (e.g., `feat/add-openai-provider`)
3. **Make your changes** and add tests for new functionality
4. **Run tests** — `poetry run pytest`
5. **Update `CHANGELOG.md`** under `[Unreleased]` using [Keep a Changelog](https://keepachangelog.com/) format
6. **Open a PR** against `main`

## Releases

Releases are triggered by pushing a `v*` tag (e.g., `v0.6.0`). CI builds the package and publishes to PyPI via trusted publishing.
