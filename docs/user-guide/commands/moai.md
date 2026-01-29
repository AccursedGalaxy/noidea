# moai

The `moai` command displays a Moai face (🗿) with witty feedback about your most recent commit, bringing a fun element to your Git workflow.

## Usage

```bash
noidea moai [options] [commit message]
```

## Description

This command displays a Moai character with your commit message. When used without flags, it simply shows the moai face and message instantly. With the `--ai` flag, it leverages AI to provide contextual, personality-driven feedback about your commit.

## Options

| Option | Description |
|--------|-------------|
| `--ai`, `-a` | Use AI to generate feedback (requires API key) |
| `--diff`, `-d` | Include the diff in AI context for better analysis |
| `--personality`, `-p` | Specify the personality to use for feedback |
| `--list-personalities`, `-l` | List all available personalities |
| `--history`, `-H` | Include recent commit history for context |
| `--debug`, `-D` | Enable debug mode to show detailed API information |

## Examples

### Basic Usage

```bash
# Show feedback for your most recent commit
noidea moai
```

### AI-Powered Feedback

```bash
# Use AI to generate more contextual feedback
noidea moai --ai
```

### Using Different Personalities

```bash
# List available personalities
noidea moai --list-personalities

# Use a specific personality
noidea moai --ai --personality supportive_mentor
```

### Including More Context

```bash
# Include diff and history for better context
noidea moai --ai --diff --history
```

## Personalities

noidea includes several built-in personalities for Moai feedback:

| Personality | Description |
|-------------|-------------|
| `professional_sass` | Professional with a hint of sass (default) |
| `snarky_reviewer` | Witty and sarcastic code reviewer |
| `supportive_mentor` | Encouraging and supportive mentor |
| `git_expert` | Technical Git expert with best practices |
| `motivational_speaker` | Energetic and motivational |

You can set your default personality in the configuration or via environment variables:

```json
# In .noidea/config.json
{
  "moai": {
    "personality": "supportive_mentor"
  }
}

# Or via environment
export NOIDEA_PERSONALITY="supportive_mentor"
```

## Custom Personalities

You can create custom personalities by creating a `personalities.toml` file in your `~/.noidea/` directory. See the [Personalities](../features/personalities.md) page for more details.

## Post-Commit Hook

When you run `noidea init` in a repository, it sets up a post-commit hook that automatically displays a moai face (without AI) after each commit. This provides instant, fun feedback without any API calls.

**To get AI-powered feedback**, run `noidea moai --ai` manually when you want deeper insights about your commit.

You can disable the post-commit hook entirely by removing or editing the `.git/hooks/post-commit` file in your repository. 