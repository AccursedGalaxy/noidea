# Hacker News — Show HN

**Title:**
Show HN: noidea – Python AI commit messages that hook into git commit and learn your repo's style

---

**Body:**

I built noidea because every AI commit message tool I found either required Node.js or generated the same boilerplate regardless of the repo it was in.

**What it does:**

noidea installs a `prepare-commit-msg` git hook. From that point on, every time you run `git commit`, it reads your staged diff, sends it to an LLM, and pre-fills your editor with a suggested message. You see it, edit it freely, and commit normally — or wipe it and write your own. Nothing is committed behind your back.

**The two things that make it different:**

1. **Repo-style learning.** Before generating, noidea samples your recent `git log` and infers your conventions — scope vocabulary, whether your commits carry a body, typical subject length, gitmoji or not — then conditions the prompt on them. In a repo that writes `feat(auth): …` with a detailed body, it writes that. In a repo with short one-liners, it writes those. The suggestions read like they belong in your history.

2. **Cost-aware model routing.** Small diffs (typo fixes, dependency bumps) go to Haiku/GPT-4o-mini. Large diffs escalate to Sonnet/GPT-4o automatically. The tool tells you which it chose on stderr. You can override with `--model`.

**Providers:** Anthropic (default), OpenAI, Gemini, DeepSeek, Groq, and local Ollama — one line in config to switch, no code change. Ollama needs no API key.

**Also a GitHub Action now**, so you can get PR comment suggestions in CI:

```yaml
- uses: AccursedGalaxy/noidea@main
  with:
    api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Install:**

```bash
pipx install noidea
noidea init   # installs the git hook
```

GitHub: https://github.com/AccursedGalaxy/noidea

Happy to answer questions about the architecture (the diff staging trick for the GitHub Action was fun to figure out) or the style-learning heuristics.

---

**Posting tips:**
- Post Tuesday–Thursday between 8–10am US Eastern for peak visibility.
- Reply promptly to every comment in the first 2 hours — HN rewards active threads.
- If you get a "what makes this different from X" question, the comparison table in the README is ready.
