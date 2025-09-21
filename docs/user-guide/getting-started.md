# Getting Started

## Smooth Setup

noidea is designed for instant value—install, init, commit.

### Step 1: Install
Download or clone, then:
```bash
./install.sh  # Sets up binary and ~/.noidea/config (AI off by default)
```

### Step 2: Init in Repo
```bash
cd your-repo
noidea init  # Installs hooks: suggestions on commit, Moai faces after
```
- Prompts: Enable suggestions? (Yes for editor magic). Interactive/full-diff optional.

### Step 3: Try It
```bash
git add .
git commit  # Opens editor with suggestion (local/AI)—edit/save!
# After: Moai face appears (no text by default).
```

**Defaults**:
- Suggestions: Always (editor pre-fill on commit).
- Moai: Faces always (text optional via AI).
- AI: Off (enable with `noidea config --init` for smarter everything).

### Enable AI (Optional)
```bash
noidea config --init  # Set provider/key/model (grok-4-fast-reasoning default)
```
Suggestions get context-aware; Moai adds text feedback.

Troubleshooting? See [Troubleshooting](../troubleshooting.md).

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