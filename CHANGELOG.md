# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/AccursedGalaxy/noidea/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/AccursedGalaxy/noidea/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/AccursedGalaxy/noidea/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AccursedGalaxy/noidea/releases/tag/v0.1.0
