# How it works

What happens between `git commit` and the suggestion in your editor, what noidea sends to the
model, and what it stores on disk.

## The commit flow

```text
git commit
  └─ prepare-commit-msg hook
       ├─ message already given (-m, --amend, merge, ...) → exit, keep it
       └─ noidea suggest --file .git/COMMIT_EDITMSG
            ├─ read the staged diff, branch name, staged file list
            ├─ read the last 50 commit messages → style hints
            ├─ pick the small or large model
            ├─ send one request to the provider
            └─ write the reply into the commit message file
  └─ git opens your editor with the message filled in
```

1. Git runs the `prepare-commit-msg` hook before it opens the editor.
2. If the commit already has a message, the hook exits in the shell and noidea does nothing else.
3. Otherwise the hook runs `noidea suggest`, which reads `git diff --cached`. Binary files appear
   as one line each that names the file, never as their contents.
4. noidea builds the request from the system prompt, the branch name, the staged file list, the
   style hints, and the diff, then picks a model and sends one request.
5. The reply is written to the commit message file and git opens your editor.

noidea never blocks a commit. If no key is configured, the provider rejects the request, times
out, or is unreachable, or `noidea` isn't on the `PATH` git runs hooks with, the hook prints the
reason and the editor opens empty, as it would without noidea.

## Model routing

noidea adds the length of the system prompt to the length of the diff, in characters. Below
`context_limit` (40,000 by default) it uses `small_model`; at or above it, `large_model`. It
prints the choice to standard error:

```text
Small diff → claude-haiku-5-5 · fast & cheap
Large change → escalating to claude-sonnet-5-5 · the strong model
```

Counting characters needs no API call, which keeps routing instant. `--model` skips routing and
prints no notice.

After routing, the diff is trimmed if it would not fit the chosen model's context window. noidea
estimates the window from the model name (200,000 tokens for Claude models, 128,000 for an
unrecognised name) and sends at most 90% of it, at 3 characters per token. Trimming drops the end
of the diff and adds a note saying how much was left out; the staged file list is always sent in
full. `diff_chars_max` sets a lower limit.

## Style learning

Before each suggestion noidea reads your last 50 commits with `git log`. With at least 5, it
measures:

- **Conventional Commits.** If 70% or more of subjects use `type(scope): ...`, suggestions do
  too, reusing your 8 most common scopes. Below 70%, suggestions drop the prefix.
- **Subject length.** Suggestions aim for your median subject length, never longer than 72
  characters.
- **Bodies.** If half or more of your commits have a body, suggestions include one. At 15% or
  fewer, they usually leave it out. In between, noidea passes the observed share along.
- **Gitmoji.** If at least half of your subjects start with a gitmoji, suggestions do too.

These hints are a few short lines added to the request. Commit messages themselves are not sent.
Turn the feature off with `learn_commit_style`.

## What leaves your machine

Each suggestion sends one request to the provider you configured, containing:

- the system prompt,
- the branch name and the list of staged file paths,
- the style hints described above,
- the staged diff, trimmed as described above.

Nothing else is sent, and noidea has no telemetry. With [Ollama](providers.md#ollama) the request
never leaves your computer. `noidea test` sends one request asking for a coding joke and contains
no repository data.

:::{warning}
The staged diff is sent as is. If you stage a file containing secrets, the provider receives
them. Check what you stage, or use a local model for sensitive repositories.
:::

## Files noidea writes

| Path | Contents | Written by |
|---|---|---|
| `~/.noidea/config.json` | User config, filled with the defaults on first run | any command |
| `~/.noidea/keys.json` | Names of the providers you stored keys for, without the keys | `noidea keys add` |
| OS keyring, service `noidea` | The API keys themselves | `noidea keys add` |
| `.git/hooks/prepare-commit-msg`, `.git/hooks/post-commit` | The hooks | `noidea init` |
| `.git/hooks/<name>.bak` | A hook noidea replaced | `noidea init` |
| `.git/noidea/` | Queued agent messages for this repository | agent backend only |
| `~/.noidea/dogfood/` | Agent run records and whether you kept each message; `$NOIDEA_DOGFOOD_DIR` moves it | agent backend only |

Hooks go to the directory in `core.hooksPath` when that is set. `noidea uninstall` removes the
hooks and `.git/noidea`; `noidea uninstall --purge` also removes `~/.noidea` and every stored key.
