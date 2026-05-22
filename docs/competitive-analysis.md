# noidea — Competitive & SEO Analysis

> Companion to [discoverability-plan.md](discoverability-plan.md). Dated 2026-05-22.
> Diagnosis stands: the code is good; **reach, positioning, and a sharp differentiator**
> are what's missing. This doc supplies the feature comparison and names two features to
> own.

---

## 1. The field (what we're up against)

| Tool | Lang | Stars (~2026) | Install | Providers (local?) | Editor-prefill hook | Standalone cmd | Multi-suggestion | Conventional | Gitmoji | Body |
|---|---|---|---|---|---|---|---|---|---|---|
| **aicommits** (Nutlope) | TS | ~9k | npm | TogetherAI/OpenAI/Groq/xAI/OpenRouter/**Ollama**/LM Studio (yes) | Yes | Yes | Yes | Yes | Yes | Yes |
| **opencommit** (`oco`) | JS/TS | ~7.3k | npm, **GH Action** | OpenAI/Anthropic/Azure/**Ollama**/Gemini/DeepSeek (yes) | Yes | Yes | No | Yes (+commitlint) | Yes | Yes |
| **aicommit2** | TS | ~0.5k | npm, **brew**, Nix | 11+ incl. Anthropic/**Ollama** (yes) | Yes | Yes (parallel race) | Yes | Yes | Yes | Yes |
| **gptcommit** | **Rust** | ~2.4k | cargo, **brew** | **OpenAI only** (no) | **Yes (hook-first)** | No | No | Yes | No | Yes (per-file) |
| **czg / cz-git AI** | TS | (big Commitizen base) | npm | OpenAI/DeepSeek/GH Models/**Ollama** (yes) | No (wizard) | Yes | Yes | Yes (core) | via cz-git | subject |
| **ai-commit** (Go) | **Go** | low | curl, go | OpenAI/Gemini/Anthropic/DeepSeek/**Ollama**/OpenRouter (yes) | unknown | Yes (TUI) | Yes | Yes | Yes | Yes |
| **lazycommit** | TS | low 100s | npm | **Groq** only | Yes | Yes | Yes | Yes | ? | ? |
| **Cursor / Copilot** (IDE) | n/a | n/a | bundled | subscription | n/a | UI button | No | partial | No | Yes |
| **→ noidea** | **Py** | **0** | **pipx/pip** | **Anthropic only** | **Yes (hook-first)** | `suggest` prints | No | Yes | No | Yes (when non-obvious) |

### What this tells us

- **Ollama / local models are table stakes**, not a differentiator. Five of eight support it. noidea's Anthropic-only stance is the single biggest *try-it blocker* (you need a paid key to even test it) — Phase 1 of the discoverability plan is correctly prioritized. But shipping Ollama only reaches **parity**; it wins nothing on its own.
- **Conventional commits + gitmoji + body** are commodity features. Everyone has them.
- **The crowded lane is "command-first, propose-and-commit, many providers."** aicommits and opencommit own it on star authority; aicommit2 out-features everyone (parallel multi-model racing, pre-commit code review, multi-VCS jj/yadm) but stays small at ~500 stars — proving features alone don't convert.
- **The real 2026 threat is not a CLI.** Cursor / Copilot / Windsurf generate commit messages zero-config, free with subscription, inside the editor. Standalone CLIs survive only on a terminal-native, hook-driven, privacy/cost-aware workflow. That's the niche to lead with — not "another AI commit CLI."

---

## 2. SEO & discoverability position

**The name is the core liability.** "noidea" carries zero category keywords (no *commit* / *git* / *ai*) and collides hard with unrelated brands (No Idea Records, No Idea Festival, NOIDEA fashion). A bare Google "noidea" returns *none* of our tool on page 1. Every competitor that ranks is self-describing — **ai**commits, **open**commit, **ai-commit**, autocommit — the name *is* the keyword. We will never win organic search on the name; we must carry keywords everywhere the name can't.

- **Page-1 anchor for every head term is `aicommits`.** It's the brand to beat and shows up on "ai commit message generator," "...cli," "best ai commit tools 2025," etc.
- **Recurring listicle tools:** aicommits, opencommit, czg, Copilot, Cursor. noidea appears in **none**. Authors need (a) stars and (b) a one-line hook. We have neither yet — section 4 fixes (b).
- **What actually drove competitor growth:** aicommits = author's large X audience + a ~60-point Show HN; opencommit = **GitHub 2023 Hackathon win** (cited in every listicle) + a modest Product Hunt. Product Hunt was minor; Reddit-driven growth was **not verifiable** for either. Lacking an author audience, our realistic levers are a strong Show HN + a one-line differentiator a listicle author can quote.
- **Legacy footprint drift:** `pkg.go.dev` still indexes the *old Go* noidea, and an April 2025 Medium post frames it as a "sassy Moai AI Git sidekick." That fragments our identity vs. the current serious Python/Claude tool. Worth cleaning up.

### ✅ Resolved 2026-05-22: Phase 0 PyPI metadata now shipped

> The discoverability plan had marked this `[x] done`, but `pyproject.toml` actually had
> none of it (description was `"You have no idea what to write? We've got you."` — zero
> keywords). It is now genuinely shipped: keyword-rich `description`, `keywords`,
> `classifiers`, and `[project.urls]` are in `pyproject.toml` (verified in the built wheel
> METADATA; `poetry check` clean, license modernized to the SPDX `MIT` expression). The
> original recommendation, for the record:

- `keywords = ["git", "commit", "ai", "conventional-commits", "cli", "claude", "anthropic", "prepare-commit-msg", "commit-message-generator", "developer-tools"]`
- full `classifiers` (Topic :: Software Development :: Version Control :: Git, etc.)
- `[project.urls]` (Homepage, Repository, Issues)
- keyword-rich `description`, e.g. *"AI commit messages that pre-fill your git editor — Claude-powered, conventional-commits aware."*

GitHub topics are also thin (`ai`, `git`, `git-hooks`, `llm`). Add the category-defining ones: `ai-commit`, `commit-message-generator`, `conventional-commits`, `git-commit`, `cli`, `anthropic`, `claude`, `pre-commit-hook`.

---

## 3. The two features to own

The brief: *find two features no one else has or does right.* Both below are (a) verified white space against the field in §1, (b) aligned with noidea's existing architecture and its safety-first TigerStyle ethos, and (c) one-line quotable for a listicle.

### Feature 1 — Repo-native style learning ("commits that look like your team's")

**The gap.** Every tool generates *generic* conventional-commit messages from a static, hard-coded system prompt. opencommit's commitlint integration only *enforces rules you hand-write*; nobody **learns the repository's actual conventions automatically.** Real repos have a voice — a scope vocabulary (`feat(provider):`, `fix(cli):`), a body habit (always / never / only-when-non-obvious), a subject length, gitmoji or not. AI tools ignore all of it and produce messages that read like a bot dropped in.

**What noidea would do.** Before generating, sample recent `git log` (subjects + bodies) and infer the repo's conventions, then condition the prompt on them: reuse the scope vocabulary already in use, match body style, match subject length, mirror gitmoji usage. Result: messages that match what the project already commits, not a generic template.

**Why noidea specifically.** We already build `_build_user_content` from branch + staged files, and the prompt is config-driven and overridable. Adding a `git log` sample to that context is a natural, small extension of the existing pipeline — and it lands squarely in the **prefill-the-editor-then-you-decide** model, where matching house style matters most.

**One-liner:** *"noidea reads how your repo already commits and writes in that voice — not generic AI boilerplate."* That's a sentence a listicle author can quote, and no competitor can.

### Feature 2 — Cost-aware automatic model routing (we already have it — sharpen and *market* it)

**The gap.** Competitors use one configured model for every commit. None route per-commit by how much thinking the diff actually needs. aicommit2 races *all* providers in parallel — the opposite trade-off: maximum cost for every commit.

**What noidea already does.** `LlmConfig.select_model()` sends small diffs to a fast/cheap model (Haiku) and escalates large diffs to a stronger one (Sonnet) automatically (`config.py:90`). This is **genuinely unique in the field** and currently buried in the config docs instead of being a headline.

**How to do it *right* (it's currently crude).** Routing is a raw character count vs. a fixed threshold. Sharpen it into a real feature:
- Route on signal, not just size — number of files, new-file vs. edit, test-only vs. source, lockfile-only.
- Make the escalation **visible** ("small diff → fast model" / "large change → escalating to the strong model") so the value is felt.
- Surface the trade-off in the pitch: trivial commits cost ~nothing and return instantly; only substantial changes pay for the strong model.

**One-liner:** *"Spends pennies and milliseconds on trivial commits; brings out the big model only when the diff actually earns it."* Pairs perfectly with the privacy/cost angle that's the standalone CLI's whole reason to exist against Copilot/Cursor.

### Supporting positioning lever (not unique enough to headline)

**"Never auto-commits — you always get the last word."** noidea (and gptcommit) prefill the editor and never commit for you, unlike the command-first majority that commit on confirm. It's a real trust differentiator that fits TigerStyle's safety-first ethos and the Show HN body already drafted — but gptcommit shares it, so use it as *reinforcement*, not the headline.

---

## 4. Recommended sequence

1. **Ship the unclaimed Phase 0 SEO** (pyproject keywords/classifiers/urls/description + GitHub topics). Free, do it this week, before the next release render.
2. **Build Feature 1 (repo-native style learning)** via grill-the-plan → TDD. This is the differentiator a listicle quotes and the thing Cursor/Copilot structurally *can't* market against a hook tool.
3. **Promote Feature 2 (cost-aware routing) to a headline** — sharpen the heuristic, make escalation visible, put it in the README's "Why noidea?" section.
4. **Close the Ollama gap (Phase 1)** for parity / try-it-without-a-key — necessary, not sufficient.
5. **Then launch** (Phase 3) with two quotable, defensible lines no incumbent has: *repo-native voice* + *cost-aware routing*.
