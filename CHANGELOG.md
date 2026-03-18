# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `--model` flag to `suggest` command for overriding the configured LLM model at runtime
- Rich spinner and status feedback to `suggest` command for better UX during API calls
- Adaptive model selection: automatically switches between `small_model` and `large_model` based on context length vs `context_limit` threshold
- Show help text when `noidea` is invoked without a subcommand

### Changed
- Replace single `model` config key with `small_model`, `large_model`, and `context_limit` for adaptive model selection
- Introduce `initialize()` to ensure config directory and files exist on startup, replacing scattered lazy-creation logic
- Use `os.makedirs(exist_ok=True)` in `install_hook` for more robust directory handling

### Fixed
- Align config tests with `initialize()` requirement by patching all necessary paths

## [0.3.0] - 2026-03-18

### Added
- `DiffResult` and `HookResult` dataclasses for explicit, typed return values from git operations

### Fixed
- Update error message to reference correct `keys add` CLI command (issue #1)
- Add error handling to git subprocess calls to prevent crashes when git is unavailable
- Create `.git/hooks` directory if missing before installing hook (supports `--no-template` repos)
- Replace `assert` with explicit `TypeError` for `TextBlock` check in provider

### Changed
- Rename `noidea keys list` to `noidea keys show` to avoid conflict with Python's `list` keyword
- Introduce `Provider` enum replacing hardcoded provider strings across config, CLI, and provider modules
- `save_key` and `remove_key` now return booleans to indicate duplicate/missing key conditions
- `list_keys` now returns data instead of printing directly; output moved to CLI layer
- Remove `pytest` from main dependencies (moved to dev group)

## [0.2.1] - 2026-03-18

### Fixed
- Wrap CLI commands in try/except for safer error handling
- Fix various typos in output and prompts
- Clarify commit message format rules in default system prompt

### Changed
- Replace TOML config with JSON and lower Python requirement to 3.10

### Added
- Initial test suite with pytest

## [0.2.0] - 2026-03-17

### Added
- Keyring-based API key management (`noidea key set/get/delete`)
- `noidea test` command to validate API key and connectivity

### Changed
- Updated README with keyring setup instructions and new command docs

## [0.1.1] - 2026-03-17

### Added
- Help strings for all CLI commands and subcommands

## [0.1.0] - 2026-03-17

### Added
- Initial release
- `noidea init` command to install git hook
- `noidea suggest` command to generate AI-powered commit messages via Anthropic
- `noidea version` and `noidea update` commands
- PyPI publishing workflow
- MIT License
- Graceful early exit when no git diff is detected

[Unreleased]: https://github.com/AccursedGalaxy/noidea/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AccursedGalaxy/noidea/releases/tag/v0.1.0
