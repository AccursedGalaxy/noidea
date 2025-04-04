#!/bin/sh
#
# post-commit hook for noidea's GitHub issue integration and Moai feedback
#
# This script runs after a commit is created and:
# 1. Processes any closing commands in commit messages to close GitHub issues
# 2. Shows a Moai face with feedback about your commit

# Define some terminal colors if supported
if [ -t 1 ]; then
    GREEN="\033[0;32m"
    YELLOW="\033[1;33m"
    CYAN="\033[0;36m"
    RED="\033[0;31m"
    RESET="\033[0m"
else
    # No colors in non-terminal environments
    GREEN=""
    YELLOW=""
    CYAN=""
    RED=""
    RESET=""
fi

# Print a divider for visual separation
print_divider() {
    echo "${CYAN}───────────────────────────────────────────────────${RESET}"
}

# Find the noidea binary in several possible locations
find_noidea() {
    # Check if it's in PATH
    if command -v noidea >/dev/null 2>&1; then
        echo "noidea"
        return 0
    fi

    # Try to determine the git root
    GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$GIT_ROOT" ]; then
        # Check common binary locations - one by one for better POSIX compatibility
        for location in "$GIT_ROOT/noidea" "$GIT_ROOT/bin/noidea" "$GIT_ROOT/build/noidea" "$GIT_ROOT/dist/noidea"; do
            if [ -x "$location" ]; then
                echo "$location"
                return 0
            fi
        done
    fi
    
    # Not found
    return 1
}

# Find the noidea binary
NOIDEA_BIN=$(find_noidea)
if [ -z "$NOIDEA_BIN" ]; then
    echo "${YELLOW}⚠️  Warning: noidea binary not found${RESET}"
    echo "${YELLOW}   Please ensure noidea is in your PATH or at the repository root${RESET}"
    exit 0
fi

# Get the last commit message
COMMIT_MSG=$(git log -1 --pretty=%B)
if [ -z "$COMMIT_MSG" ]; then
    echo "${YELLOW}⚠️  Warning: Could not get the commit message${RESET}"
    COMMIT_MSG="unknown commit"
fi

# Check if GitHub issue integration is enabled
if [ "$(git config --get noidea.github-issues)" = "true" ]; then
    # Look for closing commands in the commit message
    # Match patterns like "fixes #123", "closes #456", "resolves issue #789"
    CLOSE_PATTERN="(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)( issue)? #([0-9]+)"
    ISSUES_TO_CLOSE=$(echo "$COMMIT_MSG" | grep -i -o -E "$CLOSE_PATTERN" | grep -o -E '#[0-9]+' | sed 's/#//')
    
    # If there are issues to close, process them
    if [ -n "$ISSUES_TO_CLOSE" ]; then
        print_divider
        echo "${CYAN}🔗 Detected GitHub issue closing commands...${RESET}"
        
        # Process each issue number
        for ISSUE_NUM in $ISSUES_TO_CLOSE; do
            echo "${CYAN}Attempting to close GitHub issue #${ISSUE_NUM}...${RESET}"
            
            # Use noidea to close the issue
            if "$NOIDEA_BIN" issue close "$ISSUE_NUM" --quiet; then
                echo "${GREEN}✅ Successfully closed GitHub issue #${ISSUE_NUM}${RESET}"
            else
                echo "${RED}❌ Failed to close GitHub issue #${ISSUE_NUM}${RESET}"
                echo "${YELLOW}   You may need to close it manually or check your GitHub authentication${RESET}"
            fi
        done
    fi
fi

# Print a divider before displaying the Moai
print_divider

# Call noidea with the commit message and history context
"$NOIDEA_BIN" moai --history "$COMMIT_MSG" || echo "${RED}Error running noidea moai command${RESET}"

# Print a final divider
print_divider

# Always exit with success so git continues normally
exit 0 