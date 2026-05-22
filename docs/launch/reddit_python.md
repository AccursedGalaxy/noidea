# Reddit — r/Python

**Title:**
I got tired of AI commit message tools requiring Node.js, so I built one in Python

---

**Body:**

Every AI commit message generator I tried was an npm package. As someone who works primarily in Python and doesn't always have Node installed, that friction was annoying enough that I just… built the Python version.

**noidea** is a `pipx`-installable CLI that hooks into `git commit` via `prepare-commit-msg`. You stage your changes, run `git commit`, and your editor opens with a suggested message pre-filled. You always get the last word — nothing is committed for you.

**What makes it interesting technically:**

- **Repo-style learning:** samples your `git log` to infer your project's conventions (scope vocabulary, body habits, subject length, gitmoji), then conditions the prompt on them. Built with some lightweight heuristics — no ML, just string analysis over your recent history.
- **Cost-aware routing:** character-counts the diff to decide between fast/cheap and strong/expensive models automatically. Small diff → Haiku. Large diff → Sonnet. You're told which it used.
- **Multi-provider:** Anthropic, OpenAI, Gemini, DeepSeek, Groq, local Ollama — one line in a JSON config to switch.
- **Typed throughout:** uses a `LlmConfig` dataclass, explicit error kinds (`ErrorKind` enum), no bare `except Exception`.

Stack: `typer`, `rich`, `anthropic`, `openai`, `keyring`, `python-dotenv`. No heavy dependencies.

```bash
pipx install noidea
noidea init   # installs the git hook in the current repo
```

https://github.com/AccursedGalaxy/noidea

Would love feedback from the Python community — especially on the config system or the style-learning approach.

---

**Posting tips:**
- r/Python appreciates seeing the technical choices, not just the pitch.
- Link to specific files if commenters ask about implementation (e.g., `noidea/style.py` for the heuristics).
- Cross-post to r/learnpython if you want a different audience.
