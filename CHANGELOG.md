# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-10-16

> **Upgrading:** run `noidea init` in each repo after upgrading. A package upgrade doesn't touch the hooks already in your repos, so the hook fixes below only apply once `init` rewrites them. `noidea status` flags any hook that is out of date.

### Added
- **`noidea uninstall`** removes noidea's hooks from the current repo, puts back any hook it backed up, and deletes the per-repo state in `.git/noidea/`. `--purge` also removes your stored API keys and `~/.noidea` (it asks first; `--yes` skips the prompt) and works outside a repo too. A hook noidea didn't write, or one you edited, is left alone. Closes #10.
- **Agent backend (experimental)**: `noidea suggest --agent`, or `"use_agent": true` in the config, generates the message with the [driver-os](https://github.com/AccursedGalaxy/driver-os) commit-msg agent, which reads the repo over several turns instead of making one call. It needs the `driver-os-commit-msg` binary (on `PATH`, via `agent_binary`, or `NOIDEA_AGENT_BIN`) and falls back to the normal generator whenever the agent isn't available or fails. A message queued by `--agent` is reused by the commit hook, and a new `post-commit` hook records whether you kept, edited, or discarded it.
- **Diff size cap**: very large staged diffs (generated files, vendored trees) are trimmed to 200,000 characters (about 65,000 tokens), or less if the chosen model's context window is smaller, instead of failing the request or quietly sending a vendored tree to a 1M-token model on every commit. A visible note in the prompt says how much was left out, and the full list of changed files is always kept. Set `diff_chars_max` to pick your own limit, or `0` to let the context window alone decide.
- `noidea --version` and `noidea status` show the git commit (and `.dirty`) when running from a source checkout. Released installs still show the plain version.
- `noidea status` reports hooks that are out of date and tells you to run `noidea init`. It also shows the configured provider and where its key comes from (keyring or env var), and no longer says "no key found" when the key is in an env var.
- A new [docs site](https://noidea-ai.readthedocs.io) with pages for getting started, commands, configuration, providers, the GitHub Action, how it works, and troubleshooting.

### Fixed
- The `prepare-commit-msg` hook no longer overwrites a message you already wrote. `git commit -m`/`-F`, `-c`/`-C`/`--amend`, merges, and squashes keep their message; only a plain `git commit` (or a `commit.template`) gets a generated one. To start from a suggestion and adjust it, run `noidea suggest` and commit the edited text with `git commit -m`.
- `noidea init` could overwrite your own hook: when a `.bak` already existed it printed "skipping backup creation" and replaced the hook anyway. It now stops and tells you which file to move.
- An OpenRouter response that comes back with no choices and an upstream error in the body is now reported as a normal provider error instead of crashing on an assertion.
- noidea never blocks a commit. A missing API key used to abort `git commit`, and so did running git without `noidea` on its `PATH` (common in GUI clients and IDEs). Now the hook prints the reason and your editor opens empty.
- Errors go to stderr, and `noidea suggest` exits 1 when it produces no message. Before, errors went to stdout with exit 0, so scripts and the GitHub Action could treat the error text as the suggestion.
- Current Claude models (the 5.5 generation) work. They think before answering, which made noidea crash on the thinking block, and they reject an explicit `temperature`; noidea now reads the text block and only sends `temperature` when you change it from `1.0`.
- GitHub Action: it no longer replaces your repo's `.noidea/config.json`, so a custom `system_prompt` applies in CI. The `model` input is passed to `noidea suggest --model` instead of being written to a config file, so a model name that happens to equal an old default (such as `claude-haiku-4-5`) is no longer dropped. A failed suggestion logs the reason and adds a warning instead of posting error text, a non-Anthropic `provider` without a `model` stops with a clear error, and the model's output can no longer run as shell code.
- `.env` files are no longer loaded. An installed noidea never found the one in your repo anyway, and loading it would let a cloned repo's `.env` redirect your API key to another server. Use the keyring or real environment variables; the `python-dotenv` dependency is gone.

### Changed
- **New default models**: `claude-haiku-5-5` and `claude-sonnet-5-5` (cheaper, with a 1M-token context window), with `max_tokens` raised to 8192 to leave room for thinking. `context_limit` drops from 600,000 to 40,000 characters, so large changes actually reach the large model; before, a diff only escalated once it was already being cut down to fit.
- Defaults now reach existing users. The first run used to write every default into `~/.noidea/config.json`, which froze them there; it now writes an empty section, and values in that file that equal an old default (including the old built-in system prompts) are ignored. Values you chose, and anything in a repo config, are used as written.
- Both hooks now check in the shell whether noidea has anything to do before starting Python. A `git commit -m` used to wait about half a second for that startup; it went from 515 ms to 7 ms in our measurement.
- Re-running `noidea init` says what it actually did: "Hook installed", "Hook updated", or "already up to date". It no longer makes a `.bak` of noidea's own hook.
- noidea only treats a hook as its own when it exactly matches a script noidea has written. A hand-edited hook is yours: `init` backs it up and `uninstall` leaves it in place.

## [1.2.0] - 2026-06-02

### Added
- **OpenRouter provider support**: set `"provider": "openrouter"` to route requests through [OpenRouter](https://openrouter.ai), the OpenAI-compatible aggregator that fronts many upstream models behind one endpoint. Store a key with `noidea keys add openrouter` or the `OPENROUTER_API_KEY` env var. Because OpenRouter is an aggregator, models are addressed by their namespaced name (e.g. `anthropic/claude-3.5-sonnet`). Wired entirely through the existing OpenAI-compatible transport, so it inherits the shared error taxonomy and the reasoning-parameter fallback for free.

## [1.1.0] - 2026-05-22

### Added
- **Repo-native commit style learning** (`learn_commit_style`, on by default): before generating, noidea samples recent `git log` and infers the repo's own conventions — scope vocabulary, whether commits carry a body, typical subject length, and gitmoji usage — then conditions the prompt on them so suggestions read like the project's existing commits rather than generic boilerplate. Activates once a repo has at least 5 commits and degrades to default behaviour below that; set `"learn_commit_style": false` to disable. Sees through gitmoji prefixes (`:shortcode:` and leading emoji with variation selectors / ZWJ / skin-tone modifiers) when detecting conventional-commit subjects.
- **Visible cost-aware model routing**: `noidea suggest` now reports which model tier it selected and why (`small diff → fast & cheap` / `large change → escalating to the strong model`), printed to stderr so the `prepare-commit-msg` hook still consumes only the message. Suppressed when `--model` forces a single model.
- A "Why noidea?" section in the README leading with the project's differentiators.

### Changed
- PyPI discoverability metadata: keyword-rich `description`, `keywords`, full `classifiers`, and `[project.urls]`; license modernised to the SPDX `MIT` expression.

## [1.0.2] - 2026-05-22

### Changed
- Replace `provider.get_commit_message` with a deep `complete(system, user, model, max_tokens, temperature)` transport that owns the Anthropic client and collapses the SDK's exception hierarchy into a single `ProviderError` carrying an `ErrorKind` (auth / rate-limit / connection / status). The four-branch `except anthropic.*` ladder previously duplicated in `commands/suggest.py` and `commands/test.py` now lives once, inside `complete`; neither command imports `anthropic` any more, and a catch-all on `anthropic.APIError` keeps the SDK's error surface from leaking past the seam. Commit-prompt assembly moves to a pure `_build_user_content` helper in `suggest.py` (unit-testable without mocking the API), and `test` calls `complete` directly instead of smuggling a joke through a commit-message function. Each command keeps its own wording per `ErrorKind` behind an import-time exhaustiveness assertion.
- Return a typed, frozen `LlmConfig` dataclass from `load_config()` in place of the raw `config["llm"][...]` dict. The LLM field set — previously declared three times (`DEFAULTS` values, `_LLM_SCHEMA` types, and the `validate_config` repair loop) — now lives once in the dataclass field declarations; `DEFAULTS` is derived via `dataclasses.asdict` and `_LLM_SCHEMA`/`validate_config` are deleted. `LlmConfig.from_dict` does the warn-and-fall-back coercion (a corrupt user config warns to stderr, never crashes) and `select_model` moves onto the dataclass. `deep_merge` is retained for raw-dict composition; the typed object is constructed last, at the load boundary. The `context_limit` default is now the float `600000.0` (was int), so fresh installs show `Context Limit: 600000.0` in `noidea status`.
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

[Unreleased]: https://github.com/AccursedGalaxy/noidea/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/AccursedGalaxy/noidea/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/AccursedGalaxy/noidea/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/AccursedGalaxy/noidea/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/AccursedGalaxy/noidea/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/AccursedGalaxy/noidea/compare/v1.0.1...v1.0.2
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
