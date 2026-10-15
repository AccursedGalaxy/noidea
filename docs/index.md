# noidea

noidea writes your commit messages: it reads the staged diff when you run `git commit` and opens
your editor with a suggested message already in place.

```bash
pipx install noidea
noidea keys add
noidea init
git commit
```

[Getting started](getting-started.md) walks through each line and shows
what you see at the end.

## It writes like your repo

Before each suggestion, noidea reads your last 50 commit messages and picks up the house style:
the scopes you use, whether you write bodies, how long your subjects run, and whether you prefix
them with a gitmoji. A repo full of `fix(parser): ...` gets more of those, and a repo of plain
sentences gets plain sentences. [Style learning](how-it-works.md#style-learning) has the details.

## Small commits cost less

Every diff is measured first. Ordinary commits go to a fast, cheap model, and only very large
changes go to the strong one. noidea prints which model it picked, so the routing is never a
surprise. See [model routing](how-it-works.md#model-routing).

## You always have the last word

noidea never commits for you. The suggestion lands in your editor, where you can keep it, change
it, or delete it. Commits that already carry a message (`git commit -m`, `--amend`, merges) are
left exactly as you wrote them.

## Any model you like

Anthropic is the default. OpenAI, Gemini, DeepSeek, Groq and OpenRouter work with a key, and
[Ollama](providers.md#ollama) runs locally with no key at all.

```{toctree}
:hidden:
:caption: Guide

getting-started
providers
configuration
commands
github-action
```

```{toctree}
:hidden:
:caption: Background

how-it-works
troubleshooting
changelog
```
