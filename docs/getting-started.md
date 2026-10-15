# Getting started

This page takes you from nothing installed to your first generated commit message.

## Install

noidea needs Python 3.10 or newer. Install it with [pipx](https://pipx.pypa.io), which keeps it
in its own environment and puts the `noidea` command on your `PATH`:

```bash
pipx install noidea
```

If you do not use pipx, `pip install noidea` works too. Check the install:

```bash
noidea --version
```

## Add an API key

The default provider is Anthropic. Store your key in the operating system's keyring:

```bash
noidea keys add
```

noidea prompts for the key and hides what you type. For another provider, name it:
`noidea keys add openai`. The full list is on the [providers](providers.md) page.

On a server or in CI, where there is no keyring, export the provider's variable instead:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

:::{tip}
To try noidea without an account anywhere, point it at a local [Ollama](providers.md#ollama)
model. It needs no key.
:::

To confirm the key and the connection work, ask the model for a coding joke:

```bash
noidea test
```

## Install the hook

Run this once in each repository where you want suggestions:

```bash
cd your-repo
noidea init
```

```text
Hook installed. You're all set — commit away, we'll handle the words.
```

`noidea init` writes two git hooks, `prepare-commit-msg` and `post-commit`. If you already had a
hook with either name, noidea saves it as `<name>.bak` first. [Git hooks](commands.md#git-hooks)
describes both.

## Make your first commit

Stage something and commit without a message:

```bash
git add -p
git commit
```

noidea prints its model choice while it works:

```text
Small diff → claude-haiku-5-5 · fast & cheap
Done. You're welcome.
```

Then git opens your editor with the suggestion filled in. Save and close to commit it, edit it
first, or empty the buffer to abort the commit as usual.

## Write your own message instead

noidea only fills in a message when you have not given one. These commits keep exactly what you
wrote:

- `git commit -m "..."` and `git commit -F file`
- `git commit -c`, `-C`, and `--amend`
- merge and squash commits

To see a suggestion without committing, run `noidea suggest`. It prints the message to the
terminal, so you can copy it, adjust it, and commit with `git commit -m`.

## Next steps

- Pick a different model or provider in [Providers](providers.md).
- Tune the defaults in [Configuration](configuration.md).
- Get suggestions on pull requests with the [GitHub Action](github-action.md).
