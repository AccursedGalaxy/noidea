# Commands

Every `noidea` command, in the order `noidea --help` lists them. Each command also accepts
`--help`.

## noidea init

Installs noidea's [git hooks](#git-hooks) in the current repository. Run it once per repository,
and again after upgrading noidea, since an upgrade does not rewrite hooks that already exist.

```bash
noidea init
```

It prints what changed: `Hook installed.` on a fresh repository, `Hook updated to the latest
version.` when it replaced an older noidea hook, and `Hook already up to date.` when there was
nothing to do. A hook from another tool is saved as `<name>.bak` before noidea writes its own.
noidea respects `core.hooksPath`; if you change that setting later, run `noidea init` again.

## noidea status

Shows whether everything is wired up: the repository, both hooks, the config file, keys in the
keyring, and the models in effect.

```text
noidea v1.2.0

Repository:     ✓ git repo detected
Hook:           ✓ prepare-commit-msg installed (.git/hooks)
Hook:           ✓ post-commit installed (.git/hooks)
Config:         ✓ /home/you/.noidea/config.json loaded
API Key:        ✓ anthropic (keyring)
Small Model:    claude-haiku-4-5
Large Model:    claude-sonnet-4-6
Context Limit:  600000.0
Temperature:    1.0
```

A hook marked `outdated` needs `noidea init`. Keys supplied only through environment variables
do not appear under `API Key`.

## noidea suggest

Writes a commit message for the currently staged changes and prints it. The hook runs this
command for you on `git commit`; run it directly to preview a message.

```bash
noidea suggest
noidea suggest --model claude-sonnet-4-6
```

| Flag | Short | Default | Effect |
|---|---|---|---|
| `--model` | `-M` | | Use this model for this run, skipping [routing](how-it-works.md#model-routing). |
| `--file` | `-F` | | Write the message to this file instead of printing it. The hook uses this. |
| `--agent`, `--no-agent` | | `use_agent` | Experimental. Turn the [agent backend](configuration.md#experimental-agent-backend) on or off for this run. |

The message goes to standard output and status lines go to standard error, so
`noidea suggest > msg.txt` captures only the message.

## noidea test

Sends one small request to the configured provider and `large_model`, and prints the reply (a
coding joke). Use it to check a new key or provider before your next commit.

```bash
noidea test
```

## noidea update

Upgrades noidea with `pipx upgrade noidea`. If pipx is missing or did not install noidea, it
falls back to `pip install --upgrade noidea`. Run `noidea init` in your repositories afterwards
to refresh their hooks.

## noidea uninstall

Removes noidea's hooks from the current repository and puts back any hook it had saved as
`.bak`. It also deletes the repository's `.git/noidea` state. A hook that noidea did not write,
or one you edited, is left in place and reported.

```bash
noidea uninstall
noidea uninstall --purge
```

| Flag | Short | Effect |
|---|---|---|
| `--purge` | | Also delete every stored API key and the whole `~/.noidea` directory. Asks first. |
| `--yes` | `-y` | Skip the `--purge` confirmation. |

`--purge` works outside a repository too, for removing noidea from a machine. Run
`pipx uninstall noidea` afterwards to remove the program itself.

## noidea keys

Manages API keys in the operating system's keyring.

| Command | Effect |
|---|---|
| `noidea keys add [provider]` | Prompt for a key and store it. The provider defaults to `anthropic`. |
| `noidea keys show` | List the providers that have a stored key. Keys themselves are never printed. |
| `noidea keys remove <provider>` | Delete the stored key for that provider. |

Provider names are those in the [providers table](providers.md). Ollama needs no key.

## noidea --version

Prints the installed version. `-v` is the short form.

## Git hooks

`noidea init` installs two hooks. Both are short shell scripts you can read in `.git/hooks`.

| Hook | When git runs it | What it does |
|---|---|---|
| `prepare-commit-msg` | before the editor opens | Runs `noidea suggest` and puts the message in the editor, unless the commit already has a message. |
| `post-commit` | after the commit is made | Exits at once unless the experimental agent backend wrote this commit's message; then it records whether you kept it. |

The `prepare-commit-msg` hook leaves commits from `-m`, `-F`, `-c`, `-C`, `--amend`, merges and
squashes untouched, and decides that in the shell before Python starts, so those commits pay no
startup cost.
