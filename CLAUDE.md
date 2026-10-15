# Project Context

This project uses Poetry. Run `poetry install`, then `poetry run noidea <command>` to try the CLI
and `poetry run pytest` for the tests. Format with `poetry run black` and `poetry run isort`
(both at 100 columns).

# Coding Style

This project follows [TigerStyle](STYLE.md) — a coding style emphasizing safety, performance, and developer experience, in that order. All code contributions must adhere to this guide. Key rules to internalize:

- **Safety first:** explicit control flow, no recursion, assertions on all function arguments/return values/invariants (minimum two per function), handle all errors.
- **Zero technical debt:** do it right the first time.
- **Performance by design:** think about performance from the outset; back-of-the-envelope sketches for network, disk, memory, CPU.
- **Naming:** get the nouns and verbs right. Use `snake_case`. Do not abbreviate. Add units/qualifiers last, sorted by descending significance (e.g. `latency_ms_max`).
- **Limits:** hard limit of 70 lines per function, 100 columns per line.
- **Comments:** always say why. Comments are sentences with proper punctuation.
- **Dependencies:** be deliberate — don't pull in what you don't need, but don't rewrite battle-tested libraries (`typer`, `rich`, `anthropic`, `keyring`, etc.) for no real gain. The spirit of TigerBeetle's zero-dependency rule applies; the letter doesn't fit a Python CLI.
- **Commit messages:** descriptive, informative — explain the why, not just the what.

Read [STYLE.md](STYLE.md) in full before writing code.
