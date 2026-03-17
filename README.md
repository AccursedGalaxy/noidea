# Noidea

Simple llm powered commit suggestions that integrate with git hooks

## Architecture
config.py -> Load TOML config + env var overrides
git.py -> Run git diff --staged, return the diff string
provider.py -> Take (diff, system_prompt) -> return commit message string
cli.py -> Orchestrate the above, handle flags


## Commands

noidea suggest
1. Run git diff --staged
2. If empty → error + exit
3. Load config (env vars override optional TOML file)
4. Parse diff metadata (file list, +/- counts)
5. Truncate diff to ~12,000 chars
6. Call LLM provider → get commit message
7. Print to stdout (or write to --file path for hook use)
Flags: --file / -F (write to file, for hook), --quiet / -q (raw output only)

noidea init
1. Verify inside git repo
2. Find hooks dir (respect core.hooksPath)
3. Back up existing prepare-commit-msg if present
4. Write simple ~15-line shell hook script
5. chmod +x
