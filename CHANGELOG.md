# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Replace `provider.get_commit_message` with a deep `complete(system, user, model, max_tokens, temperature)` transport that owns the Anthropic client and collapses the SDK's exception hierarchy into a single `ProviderError` carrying an `ErrorKind` (auth / rate-limit / connection / status). The four-branch `except anthropic.*` ladder previously duplicated in `commands/suggest.py` and `commands/test.py` now lives once, inside `complete`; neither command imports `anthropic` any more, and a catch-all on `anthropic.APIError` keeps the SDK's error surface from leaking past the seam. Commit-prompt assembly moves to a pure `_build_user_content` helper in `suggest.py` (unit-testable without mocking the API), and `test` calls `complete` directly instead of smuggling a joke through a commit-message function. Each command keeps its own wording per `ErrorKind` behind an import-time exhaustiveness assertion.
- Introduce a `key_store` module that owns both API-key stores (the OS keyring secret and the `keys.json` registry) behind one interface (`add`/`remove`/`list`/`get`/`status_of`). `add` and `remove` now write both stores together and roll back on partial failure, so a failed operation leaves no half-written state. `provider.py`, `commands/keys.py`, and `commands/status.py` call this interface and no longer import `keyring` directly; the key-registry functions move out of `config.py`. Tests back the keyring with an in-memory fake instead of mocking the OS keyring.

## [1.0.1] - 2026-05-21

### Fixed
- Handle binary file diffs correctly: read `git diff` as bytes and strip binary hunks so non-UTF-8 content no longer crashes commit message generation (keeps a summary line so the AI still sees which binary files changed)

### Changed
- Bump dependencies for security and maintenance:
  - `anthropic` 0.86.0 → 0.103.1
  - `cryptography` 46.0.6 → 48.0.0
  - `idna` 3.11 → 3.15
  - `pygments` 2.19.2 → 2.20.0
  - `pytest` 9.0.2 → 9.0.3 (dev)
  - `poetry` 2.3.2 → 2.3.3 (build)

## [1.0.0] - 2026-03-28

### Added
- TigerStyle coding standard (`STYLE.md`) adapted from TigerBeetle for Python CLI context
- TigerStyle migration plan and tracking document (`docs/TIGERSTYLE_MIGRATION.md`)
- Comprehensive input validation and assertions across all modules (minimum two per function)
- Expanded test suite with validation, edge-case, and error-handling coverage

### Changed
- **Stable MVP release** — declaring the feature set stable for production use
- Narrow all `except Exception` blankets to specific exception types (`OSError`, `JSONDecodeError`, `AuthenticationError`, `RateLimitError`, `APIConnectionError`, etc.)
- Replace recursive `deep_merge` in config with iterative stack-based implementation (TigerStyle: no recursion)
- Add explicit argument and return-value validation to all public functions
- Enforce 70-line function limit and 100-column line limit across codebase
- Update `CLAUDE.md` and `CONTRIBUTING.md` to reference TigerStyle as the project coding standard

## [0.5.4] - 2026-03-20

### Added
- `temperature` config key under `llm` (default `1.0`) to control LLM output creativity; can be overridden per-user or per-repo

### Changed
- `test` command now shows a spinner while waiting for the API and returns a different joke topic each run for varied output

## [0.5.3] - 2026-03-19

### Changed
- Refine CLI output messaging across all commands for better personality and clarity
- Restructure README with clearer hierarchy and section formatting

## [0.5.2] - 2026-03-19

### Added
- `CONTRIBUTING.md` with development setup, commit conventions, and PR workflow
- `black`, `isort`, and `pyright` as dev dependencies with project-wide configuration
- `status` command showing noidea configuration, API key status, and hook installation

### Changed
- Clarify conventional commits format in the default system prompt
- Format codebase with `isort` and `black`
- Extract each CLI command into its own module under `noidea/commands/` for cleaner project structure

## [0.5.1] - 2026-03-19

### Changed
- Improve system prompt to produce bullet-point commit bodies instead of long single-line descriptions
- Refactor CLI app configuration and main callback for cleaner structure
- Clean up extra blank lines in CLI module

### Fixed
- Use config values in `test` command instead of hardcoded model

## [0.5.0] - 2026-03-18

### Added
- Branch name and staged file list as context for commit message generation
- Sphinx documentation with ReadTheDocs integration
- Asciinema demo recording

### Changed
- Compact and refine system prompt for sharper, less verbose commit messages
- Simplify model selection logic with config merging and repository-level config support
- Bump anthropic SDK to 0.86.0 and relax dependency constraints

### Fixed
- Prevent overwriting existing hook backup during `noidea init`
- Improve hook backup messaging for clarity
- Correct typo in error message

## [0.4.0] - 2026-03-18

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

[Unreleased]: https://github.com/AccursedGalaxy/noidea/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/AccursedGalaxy/noidea/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.5.4...v1.0.0
[0.5.4]: https://github.com/AccursedGalaxy/noidea/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/AccursedGalaxy/noidea/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/AccursedGalaxy/noidea/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AccursedGalaxy/noidea/releases/tag/v0.1.0
