# Configuration

Learn how to configure noidea to suit your workflow and preferences.

## Configuration Methods

noidea can be configured through:

1. **Command line options**: Temporary settings for individual commands
2. **Configuration file**: Global settings in `~/.noidea/config.json`
3. **Git config**: Repository-specific settings (mostly set by `noidea init`)
4. **Environment variables**: For API keys and global settings

## Initial Setup

Run the interactive setup assistant:

```bash
noidea config --init
```

This will walk you through setting up noidea, including AI provider selection and API key configuration.

## API Key Setup

To use AI-powered features, you need to configure an API key:

```bash
noidea config apikey
```

This securely stores your API key. See [API Key Management](../api-key-management.md) for details.

## Configuration File

The configuration file is located at `~/.noidea/config.json`. Here's an example:

```json
{
  "llm": {
    "enabled": true,
    "provider": "xai",
    "api_key": "",
    "model": "grok-4-fast-reasoning",
    "temperature": 0.7
  },
  "moai": {
    "use_lint": false,
    "faces_mode": "random",
    "personality": "snarky_reviewer",
    "personality_file": "~/.noidea/personalities.toml"
  }
}
```

### LLM Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `enabled` | Enable/disable AI features | `true` |
| `provider` | AI provider to use (xai, openai, deepseek) | `xai` |
| `model` | Model to use with the provider | `grok-4-fast-reasoning` |
| `temperature` | Randomness of responses (0.0-1.0) | `0.7` |

### Moai Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `use_lint` | Include linting results in feedback | `false` |
| `faces_mode` | Face selection mode (random, mood) | `random` |
| `personality` | Default personality for feedback | `professional_sass` |
| `include_history` | Include commit history for context | `true` |

## Git Config Settings

Most Git config settings are automatically configured when you run `noidea init`. However, you can customize them:

```bash
# Set personality for feedback
git config noidea.personality supportive_mentor

# Use full diff analysis for better suggestions
git config noidea.suggest.full-diff true

# Note: Commit message suggestions are enabled automatically by `noidea init`
```

## Environment Variables

You can use environment variables for configuration:

```bash
# API keys
export XAI_API_KEY="your_api_key_here"
export OPENAI_API_KEY="your_api_key_here"

# General settings
export NOIDEA_PERSONALITY="snarky_reviewer"
```

## Checking Current Configuration

To see your current configuration:

```bash
noidea config --show
``` 