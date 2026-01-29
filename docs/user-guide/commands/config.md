# Config Command

The `config` command allows you to manage your noidea configuration, including API keys and application settings.

## Usage

```bash
noidea config [command] [flags]
```

## Description

The config command provides several functions:
- View your current configuration
- Create or update configuration settings
- Manage API keys for AI providers
- Validate your configuration

By default, noidea stores configuration in `~/.noidea/config.json`.

## Base Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--show` | `-s` | `false` | Show current configuration |
| `--init` | `-i` | `false` | Initialize a new config file interactively |
| `--validate` | `-v` | `false` | Validate the current configuration |
| `--path` | `-p` | | Path to config file (default: ~/.noidea/config.json) |

## Subcommands

### API Key Management

| Command | Description |
|---------|-------------|
| `apikey` | Set up an API key and store it securely |
| `apikey-status` | Check API key storage status and validity |
| `apikey-remove` | Remove a stored API key |
| `clean-env` | Generate commands to clean environment variables |

## Examples

### Basic Usage

```bash
# View current configuration
noidea config --show

# Create/update configuration interactively
noidea config --init

# Validate configuration
noidea config --validate
```

### API Key Management

```bash
# Set up and securely store an API key
noidea config apikey

# Check if API key is valid and properly stored
noidea config apikey-status

# Remove a stored API key
noidea config apikey-remove

# Generate commands to clean API key environment variables
noidea config clean-env
```

## Interactive Configuration

When you run `noidea config --init`, you'll be guided through an interactive setup that lets you configure:

1. **LLM Settings**
   - Enable/disable AI integration
   - Choose AI provider (xai, openai, deepseek)
   - Set up API key
   - Select model and temperature

2. **Moai Settings**
   - Enable/disable linting feedback
   - Choose faces mode (random, sequential, mood)

3. **Personality Settings**
   - Choose from several built-in personalities
     - Professional with Sass
     - Snarky Code Reviewer
     - Supportive Mentor
     - Git Expert
     - Motivational Speaker

## API Key Security

noidea securely stores API keys using your system's native keyring/keychain when available:

- **macOS**: Uses the Keychain
- **Windows**: Uses the Windows Credential Manager
- **Linux**: Uses the Secret Service API (requires libsecret)

If the system keyring is unavailable, a fallback encrypted storage is used in `~/.noidea/secure/`.

For more details on API key management, see the [API Key Management](../features/api-key-management.md) guide.

## Related Commands

- [`init`](init.md) - Set up noidea in your repository
- [`suggest`](suggest.md) - Generate commit message suggestions
- [`moai`](moai.md) - Display feedback for your commits 