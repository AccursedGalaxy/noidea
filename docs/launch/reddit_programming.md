# Reddit — r/programming

**Title:**
I built a Python AI commit message generator that hooks into git commit and learns your repo's style (no Node.js required)

---

**Body:**

Every AI commit message tool I could find was either a Node.js package or a Rust binary. As a Python developer without a Node install, that meant juggling runtimes just to get AI-generated commit messages. So I built one in Python.

**noidea** installs a `prepare-commit-msg` git hook. Every `git commit` pre-fills your editor with an AI-suggested message. You edit it, delete it, or use it — you always get the final call.

Two things I focused on that I haven't seen in other tools:

**1. It reads your repo's own commit history before generating.** It samples your recent `git log`, detects your scope vocabulary (`feat(auth)`, `fix(api)`, etc.), whether you write bodies, your typical subject length, and gitmoji usage — then conditions the generation on those patterns. The suggestions look like they belong in your repo instead of looking like generic boilerplate.

**2. Cost-aware model routing.** Small diffs go to fast/cheap models (Haiku, GPT-4o-mini). Large diffs automatically escalate to stronger ones (Sonnet, GPT-4o). You're told which was used. No more paying $0.015 per token to describe a one-line variable rename.

Providers: Anthropic (Claude), OpenAI, Gemini, DeepSeek, Groq, and local Ollama — switch with one config line.

```bash
pipx install noidea
noidea init
```

GitHub: https://github.com/AccursedGalaxy/noidea

There's also a GitHub Action now if you want PR comment suggestions in CI.

Interested in the technical decisions — happy to discuss the style-learning heuristics or the diff staging trick for the Action.

---

**Posting tips:**
- Use r/programming for the technical angle; also cross-post to r/git and r/devops.
- Do NOT check "OC" unless it's original content — mark it correctly.
- Respond to comments within the first hour; r/programming threads decay fast.
