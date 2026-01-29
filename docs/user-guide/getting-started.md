# Getting Started

## Quick Setup

noidea is designed for instant value—install, init, commit. Get up and running in seconds.

### Step 1: Install
```bash
cd /path/to/noidea  # Or clone: git clone <repo> noidea && cd noidea
./install.sh  # Builds binary, sets up ~/.noidea/config (AI disabled by default)
```

### Step 2: Initialize in Your Repository
The magic happens here:
```bash
cd your-project
noidea init  # Installs hooks: suggestions on commit, Moai faces after
```

### Step 3: Try Your Favorite Flow
```bash
git add .
git commit  # No -m: Opens editor with AI/local suggestion pre-filled!
# Edit/save to commit. Moai face appears after (fun, no text by default).
```

**Defaults Explained**:
- **Suggestions**: Always on after init—tries local first (fast, no API), uses AI if enabled
- **Moai Faces**: Always show after commits instantly (no AI calls, keeps workflow fast)
- **AI Feedback**: Manual only—run `noidea moai --ai` when you want detailed feedback
- **AI Features**: Disabled by default (no API key needed). Enable with `noidea config --init` for smarter suggestions

### Enable AI (Optional)
For AI-powered features, configure your API key:
```bash
noidea config --init  # Set provider/key/model (grok-4-fast-reasoning default)
```
With AI enabled: Suggestions get context-aware, and you can get detailed Moai feedback via `noidea moai --ai`.

For full details, see [Configuration](configuration.md). Troubleshooting? See [Troubleshooting](troubleshooting.md).

## Introduction

noidea is a Git companion that provides AI-powered commit message suggestions and entertaining feedback after each commit, making your Git experience more enjoyable and productive.

## Prerequisites

Before you begin, make sure you have:

- Git installed and configured
- Go 1.23+ (if building from source)
- An API key from one of the supported AI providers (for AI features)

## Quick Setup

Here's how to get started in just a few minutes:

```bash
# Install noidea
git clone https://github.com/AccursedGalaxy/noidea
cd noidea
./install.sh

# Set up in your Git repo
cd /path/to/your/repo
noidea init

# Configure your API key
noidea config apikey
```

## Next Steps

After setting up noidea, check out these guides:

- [Installation Options](installation.md) - Detailed installation instructions
- [Configuration](configuration.md) - Customize noidea's behavior
- [Command Overview](commands/overview.md) - Learn about available commands

## Quick Demo

Here's a quick example of noidea in action:

1. Stage your changes with `git add .`
2. Run `git commit` (noidea will suggest a message)
3. After committing, enjoy feedback from the Moai

## Getting Help

If you encounter any issues, check out the [Troubleshooting](troubleshooting.md) section or open an issue on GitHub. 