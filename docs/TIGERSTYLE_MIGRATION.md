# TigerStyle Migration Plan

Structured TODO list for refactoring the noidea codebase to follow [STYLE.md](../STYLE.md).
Grouped by concern, ordered so each phase builds on the previous one.

> **Adapted rule:** The zero-dependency policy is relaxed for this project.
> Be deliberate about dependencies; don't rewrite battle-tested libraries.

---

## Phase 1 — Safety: Error Handling

The most impactful changes. TigerStyle says: "all errors must be handled."
Currently 7+ unprotected `open()`/`json.load()` calls and 5+ `except Exception` blankets.

- [x] **config.py — wrap file I/O in specific exception handling**
  - `load_config()`: `try/except (OSError, json.JSONDecodeError)` around both user and repo config loads.
  - `initialize()`: each `open()` and `makedirs()` wrapped in `try/except OSError`.

- [x] **config.py — eliminate recursion in `deep_merge`**
  - Replaced with iterative stack-based merge.

- [x] **commands/keys.py — narrow exception types**
  - `show()`: `except (OSError, json.JSONDecodeError)`.
  - `add()`, `remove()`: `except keyring.errors.KeyringError` + `except (OSError, json.JSONDecodeError)`.

- [x] **commands/status.py — narrow exception type**
  - `except (OSError, json.JSONDecodeError, keyring.errors.KeyringError)`.

- [x] **commands/suggest.py — narrow exception types**
  - Separate catches: `AuthenticationError`, `RateLimitError`, `APIConnectionError`, `APIStatusError`.
  - File write: `except OSError`. `KeyboardInterrupt` re-raised.

- [x] **commands/test.py — narrow exception types**
  - Same pattern as suggest.py: specific Anthropic error classes, `KeyboardInterrupt` re-raised.

- [x] **commands/update.py — narrow exception on pip fallback**
  - `except (subprocess.CalledProcessError, FileNotFoundError)`.

- [x] **provider.py — handle network errors around API call**
  - Handled at call sites (suggest.py, test.py) rather than in provider.py itself.
  - Provider stays a thin wrapper; callers catch specific Anthropic errors with actionable messages.

---

## Phase 2 — Safety: Assertions & Validation

TigerStyle: "assert all function arguments and return values."
In Python, use explicit checks that raise (`ValueError`, `TypeError`) rather than `assert`
(which is stripped by `python -O`). The spirit is the same: validate at boundaries.

- [x] **provider.py — validate `get_commit_message` inputs**
  - Check `diff` is non-empty string.
  - Check `system_prompt`, `model` are non-empty strings.
  - Check `max_tokens` is positive int, `temperature` is non-negative number.

- [x] **config.py — validate loaded config structure**
  - `_LLM_SCHEMA` dict defines expected types for each key.
  - `validate_config()` checks types after merge; bad values fall back to defaults with stderr warning.

- [x] **git.py — validate `install_hook` arguments**
  - `hooks_dir` must be a non-empty string (validated after subprocess output).
  - `HOOK_SCRIPT` module-level assertion ensures constant is non-empty.

- [x] **commands/suggest.py — validate diff before sending to API**
  - Check `diff.diff.strip()` is non-empty after `has_changes` guard.
  - File path writability handled by existing `except OSError` (no TOCTOU pre-check).

---

## Phase 3 — Function Length & Decomposition

TigerStyle: "hard limit of 70 lines per function."
Two functions currently exceed comfortable limits and pack too many concerns.

- [x] **commands/status.py — break `status()` into focused checks**
  - Extracted: `_check_repository()`, `_check_hook()`, `_check_config()`, `_check_api_keys()`.
  - Parent `status()` is now ~15 lines of orchestration.
  - `_check_hook()` uses early returns to flatten from 4 to 2 nesting levels.

- [x] **commands/suggest.py — extract model selection**
  - Extracted: `_select_model(config, context_length_chars) -> str`.
  - Pure function, moved out of the try block. Parent body now ~67 lines.

- [x] **git.py — extract backup logic from `install_hook()`**
  - Extracted: `_backup_existing_hook(hook_path) -> None`.
  - Skipped `ensure_hooks_directory` and `write_hook_script` — at 2-3 lines each they'd be trivial wrappers.

---

## Phase 4 — Control Flow Simplification

TigerStyle: "simple, explicit control flow" and "push ifs up and fors down."

- [x] **commands/status.py — flatten nested conditionals**
  - `_check_hook()` uses early returns: max 2 levels, down from 4.
  - All helpers have max 3 nesting levels.

- [x] **commands/suggest.py — separate model selection from message generation**
  - `_select_model()` is a pure decision function called before the try block.

- [x] **config.py — simplify `load_config` control flow**
  - Extracted `_collect_config_paths()` to gather paths.
  - `load_config()` iterates with a single loop — duplicated try/except eliminated.

---

## Phase 5 — Naming & Constants

TigerStyle: "get the nouns and verbs just right" and "do not abbreviate."

- [x] **Extract magic strings to module-level constants**
  - `config.py`: `SERVICE_NAME`, `CONFIG_DIR_NAME`, `CONFIG_FILENAME`, `KEYS_FILENAME`, `CONFIG_DIR`, `CONFIG_PATH`, `KEYS_PATH`.
  - `git.py`: `HOOK_NAME`, `HOOK_BACKUP_SUFFIX`, `HOOK_SCRIPT`.
  - All usage sites across `status.py`, `keys.py`, `provider.py` updated.

- [x] **Review variable names for clarity**
  - `e` → `error` in multi-line exception handlers throughout.

- [x] **Audit unit-qualified names**
  - `context_len` → `context_length_chars` in `suggest.py` with comment.
  - `context_limit` in config annotated: "Character threshold for model selection, not a token limit."

---

## Phase 6 — Comments & Documentation

TigerStyle: "always motivate, always say why."

- [x] **config.py — document the merge strategy**
  - Module docstring explains three-tier approach.
  - Inline: "Repo config merges last so project-specific settings win."
  - Inline: "Warn instead of crashing: a corrupt config should not block all CLI usage."
  - Inline: "Iterative stack-based merge to guarantee bounded execution depth."

- [x] **provider.py — document API interaction decisions**
  - Inline: "Claude can return tool_use or image blocks; we only handle text for commit messages."
  - Inline: "Keyring first: credentials stay out of the process environment."
  - Inline: "Fall back to env var for CI and headless environments."

- [x] **git.py — document subprocess patterns**
  - Inline: `check=False` comments on all 3 best-effort queries.
  - Inline: `check=True` comment on `get_diff()` explaining why failure is an error.
  - Inline: default hooks dir and backup-skip rationale.

- [x] **commands/suggest.py — document model selection heuristic**
  - Expanded comment: char count is cheap and sufficient vs real tokenization.
  - Inline: "Errors handled here (not in provider.py) because each caller needs different messages."

- [x] **Add module-level docstrings to core files**
  - `config.py`, `git.py`, `provider.py`, `cli.py`, `commands/__init__.py` — all done.

---

## Phase 7 — Line Length & Formatting

TigerStyle: "hard limit of 100 columns."

- [x] **Update Black config to 100 columns**
  - `pyproject.toml`: `line-length` 88 → 100 in `[tool.black]` and `[tool.isort]`.
  - Re-ran `poetry run black .` — 7 files reformatted (unwrapped at new limit).

- [x] **Review long string literals**
  - `config.py`: broke 2 system prompt fragments (136, 170 chars) at sentence boundaries.
  - `commands/test.py`: broke joke prompt string (101 chars).
  - Zero lines over 100 columns across all source and test files.

---

## Phase 8 — Test Hardening

TigerStyle: "tests must test exhaustively, not only with valid data but also with invalid data."

- [x] **config.py — add tests for corrupted/invalid JSON**
  - Corrupted JSON falls back to defaults, unreadable config falls back, corrupted repo uses user config.
  - `initialize()` errors: makedirs failure, config write failure — both print warnings.

- [x] **provider.py — add tests for API error paths**
  - Non-TextBlock response raises TypeError with descriptive message.

- [x] **git.py — add tests for permission errors**
  - `get_diff()`: git not found (FileNotFoundError), git command fails (CalledProcessError).
  - `install_hook()`: not in repo (None), makedirs failure (OSError).

- [x] **commands/suggest.py — add tests for edge cases**
  - AuthenticationError, RateLimitError, APIConnectionError in suggest command.
  - File write error (nonexistent directory).
  - Keys errors: show file error, add/remove keyring errors.

---

## Phase 9 — Quick Fixes

Small corrections that can be done anytime.

- [x] **Fix typo in commands/test.py**
  - `"Checkig systems..."` → `"Checking systems..."`

- [x] **config.py — use `if not keys` instead of `if keys == []`**
  - Fixed in `commands/keys.py`.

---

## Execution Notes

- **Phases 1-3 are the core refactor** — they address safety, correctness, and structure.
- **Phase 4 follows naturally** from Phase 3 (decomposition simplifies control flow).
- **Phases 5-7 are polish** — naming, comments, formatting.
- **Phase 8 strengthens the safety net** so future changes don't regress.
- **Phase 9 is trivial** — do it whenever, even as a warm-up.

Each phase is independently mergeable. Run `poetry run pytest` after every change.
