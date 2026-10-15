# docs/ convention for noidea

noidea is a public, MIT-licensed CLI on PyPI. `docs/` is the source of its documentation site,
built by Sphinx with MyST Markdown and the Furo theme and hosted on Read the Docs. Readers are
developers who found the project on GitHub or PyPI and want an answer in under a minute. This file
is the contract for anyone editing `docs/`, human or agent. Sphinx excludes it from the build.

## Ownership map

| Path | Owner | The docs agent may |
|---|---|---|
| `../README.md` | maintainer | never touch; flag drift in the SUMMARY line (see Summary line) |
| `../CHANGELOG.md` | maintainer, written with each commit | never touch |
| `../CONTRIBUTING.md` | maintainer | never touch |
| `docs/index.md` | site | fix a sentence the diff made false; never add sections |
| `docs/getting-started.md` | site | fix install, key, init, and first-commit facts |
| `docs/providers.md` | site | add, change, or remove provider rows and examples |
| `docs/configuration.md` | site | add, change, or remove config key rows and their prose |
| `docs/commands.md` | site | add, change, or remove commands, flags, and hook rows |
| `docs/github-action.md` | site | add, change, or remove action inputs, outputs, and the example |
| `docs/how-it-works.md` | site | fix the flow, hook, routing, privacy, and local-state facts |
| `docs/troubleshooting.md` | site | add or delete entries per the change table |
| `docs/changelog.md` | site | never touch; it only includes `../CHANGELOG.md` |
| `docs/conf.py`, `docs/requirements.txt`, `docs/_static/` | maintainer | never touch |
| `docs/CONVENTION.md` | maintainer | never touch |
| anything else under `docs/` | maintainer | never touch, never link from site pages |

The page set is fixed. Never create a page. If the change table points at a page that does not
exist yet, skip that part and name the missing page in the SUMMARY line.

## Single source of truth

The README is the storefront: pitch, demo, three differentiators, install in two commands, and
links into the site. It is the one page the agent cannot repair, so every fact that churns lives
on the site and nowhere else. That covers config keys, defaults, model IDs, flags, provider
endpoints, env vars, action inputs, and error strings.

Each fact has exactly one home page. Other pages link to it instead of restating it.

| Fact | Home |
|---|---|
| Config keys, types, defaults, precedence, file locations | `configuration.md` |
| Provider names, key env vars, default endpoints, keyless providers | `providers.md` |
| Commands, flags, installed hooks | `commands.md` |
| Action inputs, outputs, permissions | `github-action.md` |
| Model routing, style learning, what is sent where, local state paths | `how-it-works.md` |
| Python floor, install commands, the first commit | `getting-started.md` |
| Error messages and their fixes | `troubleshooting.md` |

## Page templates

Every page opens with one H1 and a one-sentence lede saying what the page gives the reader. No
heading named Overview, Introduction, Summary, Notes, or Conclusion.

- `index.md`: lede, a 4-line install-to-first-commit block, one short paragraph per
  differentiator (style learning, cost-aware routing, never auto-commits), then the toctree.
- `getting-started.md`: `## Install`, `## Add an API key`, `## Install the hook`,
  `## Make your first commit` (command plus the expected stderr and editor result as a `text`
  block), `## Write your own message instead`, `## Next steps` (up to 3 links).
- `providers.md`: one table (provider, needs a key, key env var, default endpoint), then one H2
  per provider family with a copy-paste config block. Local Ollama comes first after Anthropic.
- `configuration.md`: `## Where config lives`, `## All keys` (table: key, type, default,
  effect), then one H2 per behaviour that needs more than one table cell. Experimental keys go
  last under `## Experimental: agent backend`, each marked experimental in the table too.
- `commands.md`: one H2 per command in `noidea --help` order, each with a one-line purpose, an
  options table (flag, short, default, effect) when it has options, and an example. Then
  `## Git hooks` with a table of every hook `noidea init` installs and what it does.
- `github-action.md`: a complete workflow file first, then `## Inputs` and `## Outputs` tables
  in `action.yml` order, then `## Ollama in CI` and `## Repo config in CI`.
- `how-it-works.md`: `## The commit flow` (numbered steps from `git commit` to the pre-filled
  editor), `## Model routing`, `## Style learning`, `## What leaves your machine`,
  `## Files noidea writes`. Optional ASCII diagram of at most 12 lines.
- `troubleshooting.md`: one H2 per entry titled with the symptom or the exact error text the
  user sees, then a `Cause:` line and a `Fix:` line with the command or config edit.

## Look and feel

- Shell blocks use the `bash` tag and carry no `$` prompt, so the copy button yields runnable
  text. Output goes in its own `text` block below the command.
- Config examples are complete, valid JSON in a `json` block, showing only the keys the example
  is about.
- Tables for lookups, prose for reasoning, numbered lists only for ordered steps.
- Admonitions use MyST colon fences (`:::{note}`, `:::{tip}`, `:::{warning}`). At most two per
  page; a warning is reserved for data loss, cost, or something that leaves the machine.
- Links between site pages are relative `.md` links with heading anchors, for example
  `[providers](providers.md#ollama)`. Never link into files outside the site except
  `../CHANGELOG.md` through the include and GitHub URLs for source files.
- No emoji, no badges, no screenshots on site pages. The README owns the demo GIF.
- The CLI's playful help text stays in the CLI. Site prose is plain and exact.
- Write commands and flags in backticks every time: `noidea suggest --model`.
- Page caps: `index.md` 60 lines, `troubleshooting.md` 150, every other page 180. At a cap, cut
  repetition before adding anything.

## What to touch for each kind of change

| Change in the diff | Touch |
|---|---|
| Field added, changed, or removed in `LlmConfig` (`noidea/config.py`) | `configuration.md` All keys row; prose on the page that explains the behaviour |
| Provider added or changed in `_DEFAULT_BASE_URLS` or `_NO_KEY_PROVIDERS` (`noidea/provider.py`) or `_PROVIDER_ENV_VARS` (`noidea/key_store.py`) | `providers.md` table and example; `github-action.md` if the action's env block covers it |
| Command or option added, changed, or removed (`noidea/cli.py`, `noidea/commands/*.py`) | `commands.md`; `getting-started.md` only if the first-run path changed |
| Hook script or `MESSAGE_SOURCES_SUPPLIED` changed (`noidea/git.py`) | `commands.md` Git hooks; `getting-started.md` Write your own message instead; `how-it-works.md` commit flow |
| Routing, diff budget, or prompt assembly changed (`noidea/commands/suggest.py`) | `how-it-works.md` Model routing |
| Style learning changed (`noidea/style.py`) | `how-it-works.md` Style learning |
| What is sent to a provider, or a new file noidea writes | `how-it-works.md` What leaves your machine or Files noidea writes |
| User-facing error text changed (`noidea/provider.py`, `noidea/commands/*.py`) | `troubleshooting.md` entry title and fix |
| User-visible bug fixed whose symptom has a troubleshooting entry | delete that entry |
| `action.yml` inputs, outputs, or steps changed | `github-action.md` |
| Python floor or install method changed (`pyproject.toml`) | `getting-started.md` Install |
| Agent backend changed (`noidea/agent_backend.py`, `noidea/dogfood.py`, `noidea/commands/reconcile.py`) | `configuration.md` Experimental section only; never mention it on any other page |
| Hidden command such as `_reconcile` | nothing; mention only the hook that calls it |
| Refactor, rename, test, CI, dependency bump, perf not visible to users | NOOP, except fixing a symbol or path a page names |
| Docs-only turn | NOOP; never rewrite maintainer edits |

## Terms

Use these names and no synonyms.

| Term | Meaning |
|---|---|
| hook | a git hook script `noidea init` writes; name the specific hook (`prepare-commit-msg`) |
| staged diff | what `git diff --cached` shows; the only code noidea reads to write a message |
| suggestion | the generated commit message before the user commits it |
| small model, large model | the two models in `small_model` and `large_model` |
| model routing | choosing the small or large model by diff size against `context_limit` |
| style learning | matching the repo's commit conventions from recent `git log` (`learn_commit_style`) |
| provider | the LLM backend named by `llm.provider` |
| user config, repo config | `~/.noidea/config.json` and `<repo>/.noidea/config.json` |
| keyring | the OS secret store `noidea keys` writes to |
| agent backend | the experimental multi-turn generator behind `--agent` and `use_agent` |

## Freshness

Before writing any key, default, flag, env var, endpoint, model ID, hook name, or error string,
find it in the diff or in a file you opened. Zero hits: do not write it. A sentence you can no
longer verify is deleted, not hedged. Model IDs appear only as defaults copied from
`noidea/config.py` or inside provider examples. Never describe a version in prose ("since 1.1");
the changelog carries history.

## Summary line

`SUMMARY:` names each page and section touched. `NOOP:` names the change-table row that applied.
If the diff makes a statement in `../README.md` false, append `README stale: <what>` to either
line, so the maintainer can repair it by hand.
