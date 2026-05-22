# Plan: Repo-native commit style learning

> Grilled 2026-05-22. Differentiator #1 from [competitive-analysis.md](competitive-analysis.md):
> noidea reads how a repo already commits and writes in that voice, instead of generic
> conventional-commit boilerplate.
>
> **Status: implemented 2026-05-22** via TDD (20 new tests across `test_style.py`,
> `test_git.py`, `test_config.py`, `test_cli.py`; full suite 117 green, black/isort/pyright
> clean). Code lives in `noidea/style.py` (analysis + render), `noidea/git.py`
> (`Commit`, `get_recent_commits`), `noidea/config.py` (`learn_commit_style`), and
> `noidea/commands/suggest.py` (`_learn_style` wiring). Follow-up idea: rank `scopes` by
> frequency and cap to the top ~8 to keep the hint compact on repos with many scopes.

## What it does

Before generating, sample recent `git log`, distil the repo's conventions into a typed
`StyleProfile`, render it as a `Repo commit conventions:` block, and add it to the user
content alongside the existing branch/staged-files context. The model then matches the
repo's voice. Self-disables on thin history; never breaks `git commit`.

## Resolved decisions (the grill)

1. **Representation — structured profile**, not raw examples. A `StyleProfile` dataclass
   distilled from the log. Deterministic, unit-testable with zero API calls, token-compact,
   inspectable.
2. **Injection — user content.** A `Repo commit conventions:` section in
   `_build_user_content`, parallel to `Branch:`/`Staged files:`. Leaves the user-overridable
   `system_prompt` untouched; no collision logic.
3. **Precedence — quality floor + conventional toggle.** The default rules stay the quality
   floor (imperative, one-intent). Subject length **tightens only** (`min(72, median)`).
   Scope vocab and gitmoji are additive. Body habit may loosen (an extra body is never a
   quality regression). The one honored contradiction: if the repo demonstrably does **not**
   use conventional commits, drop the `type(scope):` prefix to match it.
4. **Sampling — last 50 commits, `--no-merges`, all authors**, no bot filtering in v1.
   Single fast `git log` call, ~80 prompt tokens, zero API cost.
5. **Threshold + safety — min 5 commits; never raise.** Below 5 → omit the section →
   identical to today. The extraction is best-effort (`check=False` pattern, returns `None`
   on any failure) because `prepare-commit-msg` aborts the commit on a non-zero exit. Fresh
   repo, shallow clone, and git failure all land on the safe today-behavior path.
6. **Config — on-by-default + one boolean kill-switch.** `learn_commit_style: bool = True`
   in `LlmConfig`. No size/threshold knobs in v1 (YAGNI).

## Module layout

- **`noidea/git.py`** (raw retrieval, matches its "structured dataclasses" charter):
  - `@dataclass Commit` — `subject: str`, `body: str`.
  - `get_recent_commits(count: int = 50) -> list[Commit]` — `git log -n {count} --no-merges
    --format='%s%x1f%b%x1e'`, `check=False`, returns `[]` on any failure (never raises).
- **`noidea/style.py`** (new; pure analysis + rendering):
  - `@dataclass(frozen=True) StyleProfile` with `__post_init__` invariant assertions:
    - `scopes: tuple[str, ...]` — observed conventional scopes, by frequency.
    - `conventional_ratio: float` (0–1) — subjects matching the conventional regex.
    - `body_ratio: float` (0–1) — commits with a non-empty body.
    - `subject_length_chars_median: int`.
    - `uses_gitmoji: bool`.
  - `analyze_commits(commits: list[Commit]) -> StyleProfile | None` — pure; `None` when
    `len(commits) < MIN_COMMITS`.
  - `render_profile(profile: StyleProfile) -> str` — pure; applies the §3 precedence.
  - Constants: `SAMPLE_SIZE = 50`, `MIN_COMMITS = 5`, `CONVENTIONAL_THRESHOLD = 0.7`,
    body bands (`>=0.5` include / `<=0.15` omit / else percentage), conventional + gitmoji
    regexes.
- **`noidea/config.py`** — add `learn_commit_style: bool = True` to `LlmConfig`
  (`from_dict` coercion + `__post_init__` assertion handle it like every other field).
- **`noidea/commands/suggest.py`** — wire it in; `_build_user_content` gains a
  `profile_text: str = ""` param and inserts the section between staged files and the diff.

No import cycle: `config` already imports `git`; `style` imports `Commit` from `git`;
`suggest` imports both. `StyleProfile` lives in `style`, not `config`.

### Render mapping (§3 made concrete)

- `conventional_ratio >= 0.7` → "use conventional format; scopes used here: …" ;
  else → "this repo does not use conventional-commit prefixes — match its plain style."
- subject → "aim for ~`min(72, subject_length_chars_median)` characters."
- body → high: "most commits include a short body"; low: "commits rarely include a body";
  mid: "~X% include a body."
- `uses_gitmoji` → "this repo prefixes subjects with a gitmoji — do the same."

(Thresholds 0.7 / 0.5 / 0.15 are internal constants, tunable later.)

## TDD sequence (red → green → refactor)

**Pure analysis — `analyze_commits` (no I/O, canned `list[Commit]`):**
1. returns `None` below `MIN_COMMITS` (4 commits).
2. `conventional_ratio` from a mix of conventional + plain subjects.
3. `scopes` extracted and deduped from conventional subjects.
4. `body_ratio` from commits with/without bodies.
5. `subject_length_chars_median` correct for odd/even counts.
6. `uses_gitmoji` true/false on emoji-prefixed vs plain subjects.
7. `StyleProfile.__post_init__` rejects out-of-range ratios.

**Pure rendering — `render_profile`:**
8. high conventional_ratio → instructs conventional format + lists scopes.
9. low conventional_ratio → "no prefix, plain style."
10. subject tightens (median 50 → "~50") but never loosens (median 90 → "~72").
11. body bands: high → include, low → omit, mid → percentage.
12. `uses_gitmoji` → mentions gitmoji.

**Retrieval — `get_recent_commits` (mock `subprocess.run`, per `test_git.py`):**
13. parses `%s\x1f%b\x1e` output into `Commit` list (multi-line bodies intact).
14. returns `[]` on subprocess failure — never raises.
15. invokes `--no-merges` and `-n {count}`.

**Config:**
16. `LlmConfig()` default `learn_commit_style is True`.
17. `from_dict` coerces a non-bool `learn_commit_style` to default with a warning.

**Integration — `_build_user_content` + `suggest` (via `runner.invoke`, patches):**
18. `_build_user_content` includes the section when `profile_text` is non-empty.
19. `_build_user_content` omits it when `profile_text` is empty.
20. `suggest` with `learn_commit_style=False` never calls `get_recent_commits`.
21. `suggest` with style on + sufficient history injects the profile into the content
    passed to `complete`.
22. `suggest` still succeeds when `get_recent_commits` returns `[]` (profile `None` → no
    section) — the degrade path.

## TigerStyle checklist

- Every function ≤70 lines, ≤100 cols, `snake_case`, ≥2 assertions (args + return/invariant).
- `get_recent_commits` best-effort like the existing git wrappers; explicit error handling.
- No recursion; bounded loops over the sampled commits.
- Comments say *why* (e.g., why tighten-only on subject length; why never-raise).

## Out of scope (v1)

Bot-author filtering, `--mine` author scoping, configurable sample size/threshold, raw-example
hybrid, learned-style caching across invocations.
