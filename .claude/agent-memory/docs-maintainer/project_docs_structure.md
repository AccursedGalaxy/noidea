---
name: noidea docs structure and conventions
description: Documentation layout, tooling, file purposes, and key terminology for the noidea project
type: project
---

## Documentation surfaces

- `README.md` — user-facing quick-start: install, API key setup, commands, config reference
- `CONTRIBUTING.md` — developer guide: setup, code style, commit conventions, architecture table, PR workflow
- `CHANGELOG.md` — Keep a Changelog format (https://keepachangelog.com/), Semantic Versioning; `[Unreleased]` section at top
- `docs/index.rst` — Sphinx RST source; mirrors README content in reStructuredText; built with `sphinx_rtd_theme`
- `docs/conf.py` — Sphinx config; `version` is major.minor, `release` is full semver

## Sphinx build

- Build output in `docs/build/` (gitignored) and `docs/_build/` (both exist, likely legacy)
- Theme: `sphinx_rtd_theme`
- No `source/` subdirectory — `.rst` files and `conf.py` live directly under `docs/`

## Config file format

- JSON, not TOML. Paths: `~/.noidea/config.json` (user) and `<repo>/.noidea/config.json` (repo-level)
- Three-tier merge: defaults → user config → repo config

## Architecture (as of 2026-03-19)

- `noidea/cli.py` — thin entry point, registers commands, `--version` flag
- `noidea/commands/` — one module per command: `init`, `keys`, `status`, `suggest`, `test`, `update`
- `noidea/config.py` — config loading and key management
- `noidea/git.py` — git subprocess wrappers
- `noidea/provider.py` — Anthropic API client

## CHANGELOG conventions

- Uses `[Unreleased]` section at the top
- Version dates in YYYY-MM-DD format (project uses 2026 dates — matches the environment)
- Reference links at the bottom follow GitHub compare URL pattern

## Commit conventions (for changelog entries)

- Types: feat, fix, refactor, chore, ci, docs, test
- Scopes: cli, config, git, provider
- Imperative mood, 72-char subject line, no trailing period

**Why:** Project uses Conventional Commits enforced in CI and in the noidea system prompt itself.
**How to apply:** Use same conventions when writing CHANGELOG entries and when suggesting commit messages.
