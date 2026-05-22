# dev.to / Medium article

**Title:** Why I built a Python AI commit message tool (when the Node.js ones already exist)

**Tags:** python, git, ai, devtools, opensource

---

If you search for "AI commit message generator", you'll find a handful of solid tools: [opencommit](https://github.com/di-sukharev/opencommit) (7,300+ stars), [aicommits](https://github.com/Nutlope/aicommits) (8,700+ stars), [gptcommit](https://github.com/zurawiki/gptcommit) (2,400+ stars).

They all work. So why did I build another one?

Two reasons. First: they all require Node.js or a Rust toolchain. If you're a Python developer who doesn't keep Node installed, that's friction. Second: none of them know anything about *your* repo's conventions — they generate the same boilerplate output whether you're in a monorepo with strict `feat(module):` scopes or a personal project that uses one-liners with gitmoji.

I wanted something that felt like it belonged in each repo, not like a chatbot dropped in.

## What noidea does

noidea is a Python CLI that installs a `prepare-commit-msg` git hook. From that point:

1. You stage some changes and run `git commit`
2. noidea reads the staged diff, optionally samples your `git log`, calls an LLM, and writes the result into a temp file
3. Your editor opens with the suggestion pre-filled
4. You edit, rewrite, or delete it — then save and commit normally

There's no new command to remember. It plugs into the workflow you already have.

```bash
pipx install noidea
noidea init
```

## The repo-style learning

This is the part I spent the most time on.

Before generating a message, noidea runs `git log --oneline -50` (configurable), then parses each subject line for:

- **Conventional commit prefix** — does the repo use `feat:`, `fix:`, `chore:`, etc.? What scopes appear?
- **Gitmoji** — does it use `:shortcode:` syntax, leading emoji characters, or neither?
- **Body presence** — do commits typically include a body paragraph?
- **Subject length** — what's the median character count of the first line?

That profile gets injected into the system prompt: "This repo uses conventional commits with the scopes `api`, `auth`, `db`. Commits typically have a body. Median subject length is 52 chars."

The result is suggestions that read like they belong in your project's history rather than looking like they came from a generic chatbot.

The heuristic is intentionally simple — no ML, just string parsing over 50 recent commits. It activates once a repo has at least 5 commits and stays out of the way below that.

## Cost-aware model routing

The second thing that bothered me about existing tools: they send every diff to the same model. A one-line typo fix and a 400-line refactor both go to GPT-4, or whichever you configured.

noidea measures the character count of the diff + system prompt combined and uses that as a proxy for complexity:

- Below the threshold → `small_model` (default: Claude Haiku or GPT-4o-mini)
- Above the threshold → `large_model` (default: Claude Sonnet or GPT-4o)

You're told which model ran, on stderr (so the hook's stdout stays clean). For a typo fix, you'll see "Small diff → claude-haiku-4-5 · fast & cheap". For a large refactor: "Large change → escalating to claude-sonnet-4-6 · the strong model".

You can override with `noidea suggest --model <name>` if you want to force one model.

## Multi-provider support

Switching LLM providers is a one-line config change:

```json
{ "llm": { "provider": "ollama" } }
```

Supported today: Anthropic (default), OpenAI, Google Gemini, DeepSeek, Groq, and local Ollama. The Ollama option requires no API key — if you have `ollama` running locally with a model pulled, noidea will use it.

Providers use either the native Anthropic SDK or an OpenAI-compatible transport. Reasoning models (the `o1`/`o3` family) are also supported with automatic parameter mapping.

## It's also a GitHub Action now

```yaml
- uses: AccursedGalaxy/noidea@main
  with:
    api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    post-comment: 'true'
```

This runs on PRs, applies the PR diff to the git index (so noidea's `prepare-commit-msg` path sees it as a staged diff), generates a message, and posts it as a PR comment. It uses `ollama` with `provider: ollama` and no `api-key` for a fully local, free run in self-hosted CI.

## Comparison with the existing tools

|  | **noidea** | opencommit | aicommits | gptcommit |
|--|--|--|--|--|
| Install | `pipx install noidea` | `npm i -g` | `npm i -g` | `cargo` / `brew` |
| Hooks into `git commit` | ✅ | ✅ | ✅ | ✅ |
| Learns repo style | ✅ | ❌ | ❌ | ❌ |
| Cost-aware routing | ✅ | ❌ | ❌ | ❌ |
| No Node.js required | ✅ | ❌ | ❌ | ✅ |
| GitHub Action | ✅ | ❌ | ❌ | ❌ |
| Language | Python | Node.js | Node.js | Rust |

The tools above are all good. opencommit won the GitHub 2023 Hackathon and has a huge community. aicommits is probably the most widely known. If you already have Node installed and don't care about repo-style learning, either of those will serve you well.

If you're a Python developer, or you care about your suggestions actually matching your project's conventions, noidea is for you.

## Where to get it

GitHub: https://github.com/AccursedGalaxy/noidea

PyPI: `pipx install noidea`

The code follows a strict safety-first style guide (TigerStyle from TigerBeetle, adapted for Python). PRs welcome.

---

*This article targets the keywords: ai commit message generator python, git commit message ai cli, automated commit messages, ollama commit message generator, prepare-commit-msg hook ai — to help developers who are Googling for this tool find it.*
