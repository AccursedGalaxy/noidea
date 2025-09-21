package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/AccursedGalaxy/noidea/internal/config"
)

// FindGitDir returns the path to the .git directory for the current repository.
// If not in a git repository, returns an error.
func FindGitDir() (string, error) {
	cmd := exec.Command("git", "rev-parse", "--git-dir")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("not in a git repository: %w", err)
	}

	gitDir := strings.TrimSpace(string(output))
	if gitDir == "" {
		return "", fmt.Errorf("unable to determine git directory")
	}

	// If the git dir is relative (usually .git), make it absolute
	if !filepath.IsAbs(gitDir) {
		workDir, err := os.Getwd()
		if err != nil {
			return "", fmt.Errorf("failed to get current working directory: %w", err)
		}
		gitDir = filepath.Join(workDir, gitDir)
	}

	return gitDir, nil
}

// GetScriptPath returns the absolute path to the scripts directory
func GetScriptPath() (string, error) {
	// Get the path to the current executable
	execPath, err := os.Executable()
	if err != nil {
		return "", err
	}

	// Get the directory of the executable
	execDir := filepath.Dir(execPath)

	// The scripts directory should be in the same directory as the executable
	scriptsDir := filepath.Join(execDir, "..", "scripts")

	return scriptsDir, nil
}

// InstallPostCommitHook installs the post-commit hook script in the specified
// hooks directory. The hook will call 'noidea moai' after each commit to show
// feedback about the commit message.
func InstallPostCommitHook(hooksDir string) error {
	postCommitPath := filepath.Join(hooksDir, "post-commit")

	// Create hooks directory if it doesn't exist
	if err := os.MkdirAll(hooksDir, 0755); err != nil {
		return fmt.Errorf("failed to create hooks directory: %w", err)
	}

	// If this looks like a Husky hooks directory, delegate to the Husky installer
	if isLikelyHuskyDir(hooksDir) {
		return InstallHuskyPostCommitHook(hooksDir)
	}

	// Get the absolute path to the noidea executable
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get executable path: %w", err)
	}

	// Load configuration
	cfg := config.LoadConfig()

	// Build command flags
	flags := ""

	// Add AI flag if enabled
	if cfg.LLM.Enabled {
		flags += "--ai "
	}

	// Add personality flag if set
	if cfg.Moai.Personality != "" {
		flags += fmt.Sprintf("--personality=%s ", cfg.Moai.Personality)
	}

	// Create the post-commit hook content
	hookContent := fmt.Sprintf(`#!/bin/sh
#
# noidea - Post-commit hook
# This hook calls the 'noidea moai' command after each commit
# to show a Moai face with feedback about your commit.

# Get the last commit message
COMMIT_MSG=$(git log -1 --pretty=%%B)

# Call noidea with the commit message (using absolute path)
%s moai %s"$COMMIT_MSG"

# Always exit with success so git continues normally
exit 0
`, execPath, flags)

	// Write the hook file
	if err := os.WriteFile(postCommitPath, []byte(hookContent), 0755); err != nil {
		return fmt.Errorf("failed to write post-commit hook: %w", err)
	}

	fmt.Println("Installed post-commit hook at:", postCommitPath)
	return nil
}

// InstallPrepareCommitMsgHook installs the prepare-commit-msg hook for commit message suggestions.
// This hook runs before Git creates a commit and offers AI-generated commit message suggestions
// based on the staged changes.
func InstallPrepareCommitMsgHook(hooksDir string) error {
	hookPath := filepath.Join(hooksDir, "prepare-commit-msg")

	// Create hooks directory if it doesn't exist
	if err := os.MkdirAll(hooksDir, 0755); err != nil {
		return fmt.Errorf("failed to create hooks directory: %w", err)
	}

	// If this looks like a Husky hooks directory, delegate to the Husky installer
	if isLikelyHuskyDir(hooksDir) {
		return InstallHuskyPrepareCommitMsgHook(hooksDir)
	}

	// Get the absolute path to the noidea executable
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get executable path: %w", err)
	}

	// Create the hook content
	hookContent := fmt.Sprintf(`#!/bin/sh
#
# noidea - prepare-commit-msg hook
# This hook calls 'noidea suggest' to generate commit message suggestions
# To disable, run: git config noidea.suggest false

# Define some terminal colors if supported
if [ -t 1 ]; then
    GREEN="\033[0;32m"
    YELLOW="\033[1;33m"
    CYAN="\033[0;36m"
    RED="\033[0;31m"
    RESET="\033[0m"
else
    GREEN=""
    YELLOW=""
    CYAN=""
    RED=""
    RESET=""
fi

# Get commit message file
COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Check if noidea's suggestion feature is enabled
if [ "$(git config --get noidea.suggest)" != "true" ]; then
    exit 0
fi

# Skip if it's a merge, rebase, or cherry-pick
if [ "$COMMIT_SOURCE" = "merge" ] || [ "$COMMIT_SOURCE" = "squash" ] || [ -n "$COMMIT_SOURCE" ]; then
    exit 0
fi

# Check if the commit message already has content
if [ -s "$COMMIT_MSG_FILE" ]; then
    # Has content already - user may have specified a message with -m
    # Skip if the file already has content beyond comments
    if grep -v "^#" "$COMMIT_MSG_FILE" | grep -q "[^[:space:]]"; then
        exit 0
    fi
fi

# Always use non-interactive mode for hooks to prevent stdin issues
INTERACTIVE_FLAG=""

# Get history setting from config
HISTORY_FLAG="--history 10"

# Get full diff setting from config
FULL_DIFF=$(git config --get noidea.suggest.full-diff)
if [ "$FULL_DIFF" = "true" ]; then
    DIFF_FLAG="--full-diff"
else
    DIFF_FLAG=""
fi

# Generate a suggested commit message
echo "${CYAN}🧠 Generating commit message suggestion...${RESET}"
%s suggest $INTERACTIVE_FLAG $HISTORY_FLAG $DIFF_FLAG --quiet --file "$COMMIT_MSG_FILE"

exit 0
`, execPath)

	// Write the hook file
	if err := os.WriteFile(hookPath, []byte(hookContent), 0755); err != nil {
		return fmt.Errorf("failed to write prepare-commit-msg hook: %w", err)
	}

	fmt.Println("Installed prepare-commit-msg hook at:", hookPath)
	return nil
}

// GetEffectiveHooksDir returns the directory where hooks should be installed.
// It respects `core.hooksPath` (e.g., Husky's .husky directory). When unset, it
// falls back to <gitDir>/hooks.
func GetEffectiveHooksDir() (string, error) {
	// Check if Git is available and in a repo
	gitDir, err := FindGitDir()
	if err != nil {
		return "", err
	}

	// Read core.hooksPath
	cmd := exec.Command("git", "config", "--get", "core.hooksPath")
	out, _ := cmd.Output()
	hooksPath := strings.TrimSpace(string(out))
	if hooksPath == "" {
		return filepath.Join(gitDir, "hooks"), nil
	}

	if filepath.IsAbs(hooksPath) {
		return hooksPath, nil
	}

	// Relative path -> resolve from repo root
	repoRoot, err := FindRepoRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(repoRoot, hooksPath), nil
}

// FindRepoRoot returns the absolute path to the repository root (work tree)
func FindRepoRoot() (string, error) {
	cmd := exec.Command("git", "rev-parse", "--show-toplevel")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("not in a git repository: %w", err)
	}
	repoRoot := strings.TrimSpace(string(output))
	if repoRoot == "" {
		return "", fmt.Errorf("unable to determine repository root")
	}
	return repoRoot, nil
}

// InstallHuskyPrepareCommitMsgHook installs or augments a Husky prepare-commit-msg hook
// without overwriting existing Husky logic. It appends a noidea block if not already present.
func InstallHuskyPrepareCommitMsgHook(huskyDir string) error {
	hookPath := filepath.Join(huskyDir, "prepare-commit-msg")

	// Ensure directory exists
	if err := os.MkdirAll(huskyDir, 0755); err != nil {
		return fmt.Errorf("failed to create husky directory: %w", err)
	}

	// Determine absolute executable path for reliability inside Husky envs
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get executable path: %w", err)
	}

	// Build the block we want to ensure is present
	noideaBlock := fmt.Sprintf(`
# noidea - prepare-commit-msg hook
COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

# Respect user's configuration
if [ "$(git config --get noidea.suggest)" != "true" ]; then
    exit 0
fi

# Skip for merges, squashes, and special commit sources
if [ "$COMMIT_SOURCE" = "merge" ] || [ "$COMMIT_SOURCE" = "squash" ] || [ -n "$COMMIT_SOURCE" ]; then
    exit 0
fi

# Skip if the commit message already has non-comment content
if [ -s "$COMMIT_MSG_FILE" ] && grep -v "^#" "$COMMIT_MSG_FILE" | grep -q "[^[:space:]]"; then
    exit 0
fi

# Determine diff flag from config
FULL_DIFF=$(git config --get noidea.suggest.full-diff)
if [ "$FULL_DIFF" = "true" ]; then
    DIFF_FLAG="--full-diff"
else
    DIFF_FLAG=""
fi

HISTORY_FLAG="--history 10"

echo "\033[0;36m🧠 Generating commit message suggestion...\033[0m"
"%s" suggest $HISTORY_FLAG $DIFF_FLAG --quiet --file "$COMMIT_MSG_FILE" || true
`, execPath)

	// If hook file exists, append our block if not present
	if data, err := os.ReadFile(hookPath); err == nil {
		content := string(data)
		if strings.Contains(content, "noidea - prepare-commit-msg hook") || strings.Contains(content, "noidea suggest") {
			// Already present
			return nil
		}

		// Append block with a separating newline
		updated := content
		if !strings.HasSuffix(updated, "\n") {
			updated += "\n"
		}
		updated += noideaBlock
		if err := os.WriteFile(hookPath, []byte(updated), 0755); err != nil {
			return fmt.Errorf("failed to update Husky prepare-commit-msg hook: %w", err)
		}
		fmt.Println("Updated Husky prepare-commit-msg hook at:", hookPath)
		return nil
	}

	// Create a new Husky hook with the standard husky shim then our block
	content := fmt.Sprintf(`#!/usr/bin/env sh
. "$(dirname "$0")/_/husky.sh"

%s`, noideaBlock)
	if err := os.WriteFile(hookPath, []byte(content), 0755); err != nil {
		return fmt.Errorf("failed to write Husky prepare-commit-msg hook: %w", err)
	}
	fmt.Println("Installed Husky prepare-commit-msg hook at:", hookPath)
	return nil
}

// InstallHuskyPostCommitHook installs or augments a Husky post-commit hook
// without overwriting existing Husky logic.
func InstallHuskyPostCommitHook(huskyDir string) error {
	hookPath := filepath.Join(huskyDir, "post-commit")

	if err := os.MkdirAll(huskyDir, 0755); err != nil {
		return fmt.Errorf("failed to create husky directory: %w", err)
	}

	// Determine absolute executable path and flags
	execPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get executable path: %w", err)
	}

	cfg := config.LoadConfig()
	flags := ""
	if cfg.LLM.Enabled {
		flags += "--ai "
	}
	if cfg.Moai.Personality != "" {
		flags += fmt.Sprintf("--personality=%s ", cfg.Moai.Personality)
	}

	noideaBlock := fmt.Sprintf(`
# noidea - post-commit hook
COMMIT_MSG=$(git log -1 --pretty=%%B)
"%s" moai %s"$COMMIT_MSG" || true
`, execPath, flags)

	if data, err := os.ReadFile(hookPath); err == nil {
		content := string(data)
		if strings.Contains(content, "noidea - post-commit hook") || strings.Contains(content, "moai") {
			return nil
		}
		updated := content
		if !strings.HasSuffix(updated, "\n") {
			updated += "\n"
		}
		updated += noideaBlock
		if err := os.WriteFile(hookPath, []byte(updated), 0755); err != nil {
			return fmt.Errorf("failed to update Husky post-commit hook: %w", err)
		}
		fmt.Println("Updated Husky post-commit hook at:", hookPath)
		return nil
	}

	content := fmt.Sprintf(`#!/usr/bin/env sh
. "$(dirname "$0")/_/husky.sh"

%s`, noideaBlock)
	if err := os.WriteFile(hookPath, []byte(content), 0755); err != nil {
		return fmt.Errorf("failed to write Husky post-commit hook: %w", err)
	}
	fmt.Println("Installed Husky post-commit hook at:", hookPath)
	return nil
}

// isLikelyHuskyDir returns true if the provided hooks directory appears to be managed by Husky
func isLikelyHuskyDir(hooksDir string) bool {
	// Common Husky path is ".husky" at repo root, with "_/husky.sh" present
	if strings.Contains(strings.ToLower(hooksDir), ".husky") {
		if _, err := os.Stat(filepath.Join(hooksDir, "_", "husky.sh")); err == nil {
			return true
		}
		if filepath.Base(hooksDir) == ".husky" {
			return true
		}
	}
	return false
}
