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

When you set `provider` to anything other than `anthropic`, also set `model`. Otherwise the
action asks the new provider for the default Anthropic model names.

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

The action writes its own `.noidea/config.json` in the checkout with the `provider` and `model`
inputs, replacing any repo config committed there for that run. Settings such as
`system_prompt` from your repo config therefore do not apply in the action.
