# Git Integration

noidea integrates seamlessly with Git through hooks and extensions, enhancing your Git workflow without getting in the way.

## Git Hooks

When you run `noidea init` in a repository, it sets up several Git hooks:

### prepare-commit-msg

This hook is triggered before a commit message editor is displayed. It:

- Analyzes your staged changes
- Generates a professionally formatted commit message suggestion
- Pre-fills your commit message template

This makes it easy to create consistent, descriptive commit messages without extra effort.

### post-commit

After each commit, this hook:

- Runs the `noidea moai` command (without AI)
- Instantly displays a Moai face with your commit message
- Provides a fun, visual confirmation without making API calls

**Note:** AI-powered feedback is not automatic. Run `noidea moai --ai` manually when you want detailed, AI-generated analysis of your commit.

## Git Command Extension

noidea can be used as a Git subcommand, allowing you to run:

```bash
git noidea <command>
```

This is enabled during installation by creating a Git alias.

## Manual Hook Installation

If you prefer to manually set up the hooks:

```bash
# Copy the hook scripts to your .git/hooks directory
cp scripts/prepare-commit-msg .git/hooks/
cp scripts/post-commit.sh .git/hooks/post-commit

# Make them executable
chmod +x .git/hooks/prepare-commit-msg
chmod +x .git/hooks/post-commit
```

## Disabling Hooks

You can disable hooks temporarily by:

```bash
# Skip all hooks for a specific commit
git commit --no-verify -m "your message"

# Disable commit suggestions permanently
git config noidea.suggest false
```

## Best Practices

For the best experience with noidea's Git integration:

1. **Make focused commits** - Commit related changes together for better suggestions
2. **Use conventional commit format** - This helps noidea understand your commit patterns
3. **Install noidea hooks in each repository** - Run `noidea init` in each repo you want to use it in

## Troubleshooting

If hooks aren't working:

1. Verify the hooks are executable: `ls -la .git/hooks/`
2. Ensure noidea is in your PATH: `which noidea`
3. Check Git hooks are enabled: `git config core.hooksPath` 