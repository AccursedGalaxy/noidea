# Product Hunt

## Tagline (60 chars max)
AI commit messages that learn your repo's style

## Description (260 chars)
noidea hooks into `git commit` and pre-fills your editor with an AI-suggested message — no new command to learn. It reads your repo's own commit history to match your conventions, routes small diffs to cheap models automatically, and supports Claude, GPT, Ollama, and more.

## First comment (maker comment — post within 5 min of going live)

Hey Product Hunt! 👋

I built noidea out of pure frustration: every AI commit message tool I found either needed Node.js (I'm a Python dev) or produced the same boilerplate regardless of which repo I was in.

**The two bets I made that I haven't seen elsewhere:**

1. **Style learning from your own history.** Before generating anything, noidea reads your recent `git log` and figures out your conventions — your scope prefixes, whether you use gitmoji, how long your subjects usually are — then matches them. In a monorepo with strict `feat(module):` prefixes it'll use those. In a startup repo with casual one-liners it'll use those instead.

2. **Automatic cost routing.** Small diff = fast, cheap model. Large diff = strong model. You're told which one ran. No more paying premium rates to describe a one-line fix.

**How it works:** one `prepare-commit-msg` hook. Every `git commit` pre-fills your editor with the suggestion. Edit it, delete it, or use it — you always decide.

```bash
pipx install noidea
noidea init
```

Would love to hear what you think, especially from anyone who's tried the other tools in this space. Happy to answer any questions about the technical decisions.

## Topics / Categories
- Developer Tools
- Productivity
- Artificial Intelligence
- Open Source

## Links
- Website / GitHub: https://github.com/AccursedGalaxy/noidea
- PyPI: https://pypi.org/project/noidea/

## Gallery captions (for screenshots/GIFs)
1. "One command to hook in — every `git commit` from that point pre-fills your editor"
2. "noidea samples your git log to match the repo's own scope vocabulary and body style"
3. "Small diff? Fast cheap model. Large change? Escalates automatically — and tells you"
4. "Supports Claude, GPT-4, local Ollama, Gemini, DeepSeek, Groq — one config line to switch"
5. "Works as a GitHub Action too: AI commit suggestions posted as PR comments"

## Posting tips
- Launch on a Tuesday, Wednesday, or Thursday — not Monday (competitive) or Friday (low traffic).
- Reply to every comment in the first hour; PH surface your listing more when it has active engagement.
- Ask 3–5 friends to upvote at launch, but not all at once (PH detects coordinated voting).
- Tag relevant makers in your first comment (other dev-tool makers who might genuinely find it useful).
