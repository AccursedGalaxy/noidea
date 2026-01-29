# Init Command

The `init` command sets up noidea in your Git repository by installing Git hooks that enable commit suggestions and Moai feedback.

## Usage

```bash
noidea init [flags]
```

## Description

When you run `noidea init`, it:

1. Checks if Git is installed and properly configured
2. Verifies you're in a Git repository
3. Creates and installs the necessary Git hooks:
   - `post-commit` hook for displaying Moai feedback after commits
   - `prepare-commit-msg` hook for generating commit message suggestions

If existing hooks are found, noidea automatically creates backups with a `.bak` extension before installing its own hooks.

## Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--suggest` | `-s` | `true` | Enable commit message suggestions |
| `--interactive` | `-i` | `false` | Enable interactive mode for direct command usage |
| `--full-diff` | `-f` | `false` | Include full diffs in commit message analysis |
| `--force` | `-F` | `false` | Force installation even if checks fail |

## Examples

### Basic Installation

```bash
# Navigate to your repository
cd /path/to/your/repo

# Initialize noidea with default settings
noidea init
```

### Customized Installation

```bash
# Enable interactive mode and full diff analysis
noidea init --interactive --full-diff

# Disable commit suggestions
noidea init --suggest=false

# Force installation even if issues are detected
noidea init --force
```

## Post-Installation

After installation, you can modify settings using Git config:

```bash
# Enable/disable commit suggestions
git config noidea.suggest true   # Enable
git config noidea.suggest false  # Disable

# Change interactive mode
git config noidea.suggest.interactive true

# Change full diff analysis
git config noidea.suggest.full-diff true
```

## AI Feedback

The post-commit hook displays a moai face instantly (without AI) to keep your workflow fast. When you want detailed AI-powered feedback about a commit, run:

```bash
noidea moai --ai
```

This gives you control over when to make LLM API calls, keeping your regular commit workflow quick and responsive.

## API Key Configuration

For the best experience with commit suggestions, configure an API key:

```bash
# Configure interactively
noidea config --init

# Or set the API key directly
noidea config apikey
```

Without an API key, noidea will fall back to a simpler local algorithm for generating commit messages.

## Related Commands

- [`suggest`](suggest.md) - Generate commit message suggestions
- [`moai`](moai.md) - Display feedback for your commits
- [`config`](config.md) - Configure noidea settings 