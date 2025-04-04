#!/bin/bash
#
# install-hooks.sh - Install Git hooks for noidea
#
# This script installs Git hooks from the noidea package
# into your current Git repository.

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create hooks directory if it doesn't exist
hooks_dir=".git/hooks"
if [ ! -d "$hooks_dir" ]; then
    echo -e "${YELLOW}Warning: .git/hooks directory not found${NC}"
    echo "Are you sure you're in a Git repository?"
    exit 1
fi

# Get the repository root
GIT_ROOT=$(git rev-parse --show-toplevel)

# Function to install a hook
install_hook() {
    hook_name=$1
    source_file="$(dirname "$0")/$hook_name"
    target_file="$hooks_dir/$hook_name"
    
    # Check if source file exists
    if [ ! -f "$source_file" ]; then
        echo -e "${RED}Error: Source hook file not found: $source_file${NC}"
        return 1
    fi
    
    # Copy the hook file
    cp "$source_file" "$target_file"
    
    # Make the hook executable
    chmod +x "$target_file"
    
    echo -e "${GREEN}✓${NC} Installed $hook_name hook"
}

# Install the post-commit hook
install_hook "post-commit.sh"

# Install the prepare-commit-msg hook
install_hook "prepare-commit-msg"

# Enable noidea's commit message suggestions
git config noidea.suggest true
echo -e "${GREEN}Enabled commit message suggestions${NC}"

# Ask about interactive mode
echo -e "${BLUE}Note:${NC} Interactive mode only applies when running 'noidea suggest' directly."
echo "      Git hooks always use non-interactive mode to avoid input issues."
echo "      You can still edit the message in your editor after suggestion."
read -p "Do you want to enable interactive mode for direct command usage? (y/N) " ENABLE_INTERACTIVE

if [ "${ENABLE_INTERACTIVE}" = "y" ] || [ "${ENABLE_INTERACTIVE}" = "Y" ]; then
    git config noidea.suggest.interactive true
    echo -e "${GREEN}Enabled interactive mode for direct command usage${NC}"
else
    git config noidea.suggest.interactive false
    echo -e "${GREEN}Disabled interactive mode${NC}"
fi

# Ask about full diff mode
read -p "Do you want to include full diffs in analysis? (Y/n) " ENABLE_FULL_DIFF

if [ "${ENABLE_FULL_DIFF}" = "n" ] || [ "${ENABLE_FULL_DIFF}" = "N" ]; then
    git config noidea.suggest.full-diff false
    echo -e "${GREEN}Disabled full diff analysis${NC}"
else
    git config noidea.suggest.full-diff true
    echo -e "${GREEN}Enabled full diff analysis${NC}"
fi

# Ask if the user wants to enable GitHub issue integration
echo ""
echo -e "${CYAN}Would you like to enable GitHub issue integration?${NC}"
echo "This allows noidea to link commits to issues and close issues from commit messages."
echo "For example, typing 'fixes #123' in a commit message will automatically close issue #123."
read -p "Enable GitHub issue integration? [y/N] " ENABLE_GITHUB

if [ "${ENABLE_GITHUB}" = "y" ] || [ "${ENABLE_GITHUB}" = "Y" ]; then
    git config noidea.github-issues true
    echo -e "${GREEN}GitHub issue integration enabled${NC}"
    
    # Check if we already have a GitHub token configured
    if command -v noidea >/dev/null 2>&1; then
        echo "Checking GitHub authentication..."
        if noidea config github-auth-status >/dev/null 2>&1; then
            echo -e "${GREEN}GitHub authentication already configured${NC}"
        else
            echo -e "${YELLOW}You'll need to set up GitHub authentication with:${NC}"
            echo "  noidea config github-auth"
        fi
    else
        echo -e "${YELLOW}After installing noidea, you'll need to set up GitHub authentication with:${NC}"
        echo "  noidea config github-auth"
    fi
else
    git config noidea.github-issues false
    echo -e "${YELLOW}GitHub issue integration not enabled${NC}"
fi

echo -e "\n${GREEN}✓${NC} Git hooks installation complete"
echo "To uninstall, run: git config noidea.suggest false"
echo "To change settings, use: git config noidea.suggest.interactive [true|false]"
echo "                          git config noidea.suggest.full-diff [true|false]"
echo ""
echo "Note: Commit message suggestions always use a professional format"
echo "      regardless of any personality settings used elsewhere in noidea." 