# noidea Discoverability Plan

> Working doc. Diagnosis: the code is fine; **reach and positioning are the problem.**
> Stars = reach × conversion, and reach is currently ~0. This plan fixes both, in order.

## Guiding principle

You get **one** Show HN and one "first impression" per channel. Do not spend them
until (a) the multi-provider gap is closed and (b) the conversion surfaces (README,
PyPI page, social preview) are sharp. Launching Anthropic-only invites the
"why not Ollama/OpenAI?" top comment that kills momentum.

---

## Phase 0 — Quick wins (do now, minutes)

- [x] **PyPI metadata** — added `keywords`, full `classifiers`, `[project.urls]`,
  keyword-rich `description` in `pyproject.toml`. Ships on next release.
- [x] **README repositioning** — H1 now leads with the function; added a "Why noidea?"
  section that differentiates honestly against aicommits/opencommit.
- [x] **GitHub topics** — added (commit, conventional-commits, ollama, openai, deepseek, groq, …):
  ```bash
  gh repo edit AccursedGalaxy/noidea \
    --add-topic commit --add-topic commit-messages --add-topic git-commit \
    --add-topic conventional-commits --add-topic cli --add-topic command-line \
    --add-topic python --add-topic anthropic --add-topic claude \
    --add-topic developer-tools --add-topic prepare-commit-msg --add-topic productivity
  ```
- [ ] **Custom OpenGraph image** — repo currently uses GitHub's default gray preview.
  A 1280×640 PNG with the name + one-line value prop makes every shared link look
  intentional. Upload via repo Settings → Social preview.
- [x] **Enable Discussions** — a low-friction place for "how do I…" that doesn't clutter
  Issues, and a signal the project is alive.

## Phase 1 — Close the credibility gap (the gating build)

> **Status: shipped.** Multi-provider landed (PR #28: Anthropic/OpenAI/Ollama/Gemini/
> DeepSeek/Groq; PR #33: OpenRouter). README now says "works with Claude, GPT, local Ollama."

**Multi-provider support (OpenAI + Ollama).** This is the single biggest functional
gap vs. every incumbent, and the #1 try-it blocker: today you cannot even *try* noidea
without a paid Anthropic key. Ollama removes that blocker entirely (free + local).

- Recommended approach: go through grill-the-plan → TDD red-green-refactor (project
  workflow). Treat it as a `Provider` abstraction behind the existing `complete()`
  transport, with Anthropic / OpenAI / Ollama implementations and config-driven
  selection. Keep TigerStyle (assertions, ≤70-line functions, explicit errors).
- README + docs then say "works with Claude, GPT, and local Ollama models" — which is
  the line that makes the launch land.

## Phase 2 — Widen install paths

- [x] **GitHub Action** — published (PR #31). opencommit's
  Action is a real discovery surface; the Marketplace is searchable and indexed.
- [ ] **Homebrew formula** — `brew install noidea`. Removes the "is pipx even installed?"
  friction for Mac users.
- [ ] Keep pipx/pip as the primary path; these are additive.

## Phase 3 — Launch (one shot — do it well)

Prerequisite: Phases 0–1 done, demo GIF current, README sharp.

### Show HN
- Title: `Show HN: noidea – AI git commit messages that pre-fill your editor (Claude/GPT/Ollama)`
- Post body (draft):
  > I kept writing lazy one-word commit messages, so I built noidea. After a one-time
  > `noidea init`, every `git commit` opens your editor with a suggested message already
  > filled in from your staged diff — no new command, and it never auto-commits, so you
  > always get the last word. Small diffs use a fast/cheap model; large diffs escalate
  > automatically. Works with Claude, GPT, and local Ollama. It's a small Python CLI,
  > MIT, built to a strict safety-first style guide. Feedback welcome — especially on
  > the prompt and the model-switching heuristic.
- Post Tue–Thu, ~8–10am ET. Reply to every comment in the first 2 hours.

### Reddit
- r/programming, r/git, r/commandline, r/Python. **Different framing per sub** — no
  cross-posting the same text. Lead with the problem, not the tool. Link the repo, not a
  blog. Be present in comments.

## Phase 4 — Slow-burn durable discovery

- [ ] **Awesome-list PRs** (durable backlinks + SEO):
  - `agarrharr/awesome-cli-apps` (Git section)
  - `dictcp/awesome-git` / `git-tips`-style lists
  - `sindresorhus/awesome` adjacent dev-tool lists
  - any "awesome-claude" / "awesome-llm-tools" lists
  - Each PR: one clean line, alphabetical, matches the list's format exactly.
- [ ] **Comparison SEO** — a short "noidea vs aicommits vs opencommit" section in docs
  captures the high-intent search traffic ("ai commit tool comparison").

---

## Scorecard (revisit monthly)

| Signal | Baseline (2026-05-22) | Target 90d |
|--------|----------------------|-----------|
| GitHub stars | 0 | 100+ |
| PyPI monthly downloads | ~unknown | 500+ |
| Providers supported | 1 (Anthropic) | 3 (Anthropic/OpenAI/Ollama) |
| Install paths | pipx/pip | + Homebrew + Action |
| Awesome-list entries | 0 | 3+ |
