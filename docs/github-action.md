# GitHub Action

The noidea action suggests a commit message for every pull request and posts it as a comment, so
whoever squash-merges the PR has a message ready.

```yaml
# .github/workflows/noidea.yml
name: Commit message suggestion
on: [pull_request]

jobs:
  suggest:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: AccursedGalaxy/noidea@main
        with:
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add your provider key as a repository secret under **Settings → Secrets and variables →
Actions**. `fetch-depth: 0` gives the action the base branch history it diffs against, and
`pull-requests: write` lets it post the comment.

The action installs noidea from PyPI, stages the pull request's diff against its base branch, and
runs `noidea suggest` on it. Model routing applies as it does locally.

## Inputs

| Input | Default | Effect |
|---|---|---|
| `api-key` | `""` | Key for the chosen provider. Pass it from a secret. Not needed for `ollama`. |
| `provider` | `anthropic` | One of `anthropic`, `openai`, `ollama`, `gemini`, `deepseek`, `groq`, `openrouter`. |
| `model` | `""` | Use this one model. Empty means automatic routing between the default small and large models. |
| `post-comment` | `"true"` | Post the suggestion as a PR comment. Set `"false"` to only use the output. |
| `github-token` | `${{ github.token }}` | Token used to post the comment. |

When you set `provider` to anything other than `anthropic`, you must also set `model`, because
the default models are Claude models. The action stops with an error if `model` is missing.

If a suggestion fails (a bad key, a rate limit, a provider outage), the step logs the reason and
adds a warning, but it doesn't fail your PR checks. The output is then empty and no comment is
posted.

## Outputs

| Output | Value |
|---|---|
| `commit-message` | The suggested message. |

Read the output in a later step:

```yaml
      - uses: AccursedGalaxy/noidea@main
        id: noidea
        with:
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          post-comment: "false"
      - env:
          MESSAGE: ${{ steps.noidea.outputs.commit-message }}
        run: printf '%s\n' "$MESSAGE"
```

Pass the output through `env` as shown, not by writing `${{ ... }}` inside `run`, so text from
the model can never run as shell code.

## Ollama in CI

The `ollama` provider needs no key, but it does need an Ollama server listening on
`localhost:11434` inside the job, with the model already pulled. The action does not start one,
so add those steps before it and set `model` to the model you pulled.

## Repo config in CI

The action writes the `provider` and `model` inputs to the runner's user config
(`~/.noidea/config.json`) and leaves your checkout untouched. A `.noidea/config.json` committed in
your repo still applies on top, so settings such as `system_prompt` work in CI too. If your repo
config also sets `provider` or the models, the repo config wins.
