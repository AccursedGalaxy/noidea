#!/bin/bash
#
# noidea - Simple installation script
#
# This script:
# 1. Builds the noidea binary
# 2. Installs it to /usr/local/bin (or custom location)
# 3. Creates the ~/.noidea directory for configuration
# 4. Installs the necessary Git hooks and scripts
#

set -e

# Text formatting
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Preserve the real user and their home directory
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)

# Default installation directory
INSTALL_DIR="/usr/local/bin"
if [ -n "$1" ]; then
    INSTALL_DIR="$1"
fi

# Current script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🧠 noidea installer${NC}"
echo "============================="

# Find Go - try different approaches
find_go() {
    # First check if go is directly available
    if command -v go &> /dev/null; then
        echo "go"
        return 0
    fi

    # Check common Go installation paths
    for path in "/usr/local/go/bin/go" "/usr/lib/go/bin/go" "/usr/bin/go" "$HOME/go/bin/go" "$HOME/.local/bin/go"; do
        if [ -x "$path" ]; then
            echo "$path"
            return 0
        fi
    done

    # If running as sudo, try the real user's PATH
    if [ -n "$SUDO_USER" ]; then
        # Get the real user's PATH
        USER_PATH=$(sudo -u "$SUDO_USER" bash -c 'echo $PATH')
        
        # Check each directory in the user's PATH
        IFS=':' read -r -a path_dirs <<< "$USER_PATH"
        for dir in "${path_dirs[@]}"; do
            if [ -x "$dir/go" ]; then
                echo "$dir/go"
                return 0
            fi
        done
    fi

    return 1
}

# Try to find Go
GO_CMD=$(find_go)

if [ -z "$GO_CMD" ]; then
    echo -e "${RED}Error: Go is not installed or not found in common locations${NC}"
    echo "Please install Go from https://golang.org/dl/"
    exit 1
fi

echo "Using Go at: $GO_CMD"

# Check if directory exists and is writable
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory $INSTALL_DIR does not exist. Creating it...${NC}"
    if ! mkdir -p "$INSTALL_DIR" 2>/dev/null; then
        echo -e "${RED}Error: Failed to create $INSTALL_DIR${NC}"
        if [ "$(id -u)" -ne 0 ]; then
            echo "Try running with sudo: sudo ./install.sh"
        fi
        exit 1
    fi
fi

if [ ! -w "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Cannot write to $INSTALL_DIR${NC}"
    if [ "$(id -u)" -ne 0 ]; then
        echo "Try running with sudo: sudo ./install.sh"
    fi
    exit 1
fi

# Create config directory for the real user
CONFIG_DIR="$REAL_HOME/.noidea"
echo "Creating config directory at $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"
# If running as root, ensure the directory is owned by the real user
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER" "$CONFIG_DIR"
fi

# Copy personalities.toml.example to the config directory
echo "Installing personality configurations"
cp "$SCRIPT_DIR/personalities.toml.example" "$CONFIG_DIR/personalities.toml"
# If running as root, ensure the file is owned by the real user
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    chown "$SUDO_USER" "$CONFIG_DIR/personalities.toml"
fi

# Interactive configuration setup
setup_config() {
    CONFIG_FILE="$CONFIG_DIR/config.json"
    echo -e "\n${CYAN}Setting up noidea configuration...${NC}"
    
    # Check if config already exists and ask about overwriting
    if [ -f "$CONFIG_FILE" ]; then
        read -p "Configuration file already exists. Overwrite? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Keeping existing configuration.${NC}"
            return
        fi
    fi
    
    # Create empty JSON config
    cat > "$CONFIG_FILE" << EOF
{
  "llm": {
    "enabled": false,
    "provider": "xai",
    "api_key": "",
    "model": "grok-4-fast-reasoning",
    "temperature": 0.7
  },
  "moai": {
    "use_lint": false,
    "faces_mode": "random",
    "personality": "snarky_reviewer",
    "personality_file": "$CONFIG_DIR/personalities.json"
  }
}
EOF

    # LLM Settings
    echo -e "\n${CYAN}📚 AI Integration${NC}"
    read -p "Enable AI-powered features? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Use sed to update JSON values
        sed -i 's/"enabled": false/"enabled": true/g' "$CONFIG_FILE"
        
        # Provider selection
        echo -e "\nSelect AI provider:"
        echo "1) xAI (Grok models)"
        echo "2) OpenAI"
        echo "3) DeepSeek (experimental)"
        read -p "Choose a provider (1-3): " provider_choice
        echo
        
        case $provider_choice in
            1)
                sed -i 's/"provider": "xai"/"provider": "xai"/g' "$CONFIG_FILE"
                sed -i 's/"model": "grok-4-fast-reasoning"/"model": "grok-4-fast-reasoning"/g' "$CONFIG_FILE"
                ;;
            2)
                sed -i 's/"provider": "xai"/"provider": "openai"/g' "$CONFIG_FILE"
                sed -i 's/"model": "grok-4-fast-reasoning"/"model": "gpt-3.5-turbo"/g' "$CONFIG_FILE"
                ;;
            3)
                sed -i 's/"provider": "xai"/"provider": "deepseek"/g' "$CONFIG_FILE"
                sed -i 's/"model": "grok-4-fast-reasoning"/"model": "deepseek-chat"/g' "$CONFIG_FILE"
                ;;
            *)
                # Default case, keep xAI
                ;;
        esac
        
        # API Key
        read -p "Enter your API key (required for AI features, will be stored securely): " api_key
        if [ -n "$api_key" ]; then
            # Store the API key temporarily in the config file
            # It will be moved to secure storage on first run
            api_key_escaped=$(echo "$api_key" | sed 's/[\/&]/\\&/g')
            sed -i "s/\"api_key\": \"\"/\"api_key\": \"$api_key_escaped\"/g" "$CONFIG_FILE"
            
            # Note about secure storage
            echo -e "${GREEN}✓${NC} API key will be moved to secure storage on first run"
        else
            echo -e "${YELLOW}⚠️  Warning: No API key provided. AI features will not work properly.${NC}"
            echo -e "${YELLOW}   You can add your API key later with: noidea config apikey${NC}"
        fi
        
        # Temperature setting
        read -p "Creative temperature (0.0-1.0, default 0.7): " temperature
        if [ -n "$temperature" ]; then
            sed -i "s/\"temperature\": 0.7/\"temperature\": $temperature/g" "$CONFIG_FILE"
        fi
    fi
    
    # Personality Settings
    echo -e "\n${CYAN}🤖 Personality Settings${NC}"
    echo "Choose a default personality for AI feedback:"
    echo "1) Snarky Code Reviewer (witty and sarcastic)"
    echo "2) Supportive Mentor (encouraging and positive)"
    echo "3) Git Expert (technical and professional)"
    read -p "Choose a personality (1-3): " personality_choice
    echo
    
    case $personality_choice in
        1)
            sed -i 's/"personality": "snarky_reviewer"/"personality": "snarky_reviewer"/g' "$CONFIG_FILE"
            ;;
        2)
            sed -i 's/"personality": "snarky_reviewer"/"personality": "supportive_mentor"/g' "$CONFIG_FILE"
            ;;
        3)
            sed -i 's/"personality": "snarky_reviewer"/"personality": "git_expert"/g' "$CONFIG_FILE"
            ;;
        *)
            # Default case, keep snarky_reviewer
            ;;
    esac
    
    # Moai face settings
    echo -e "\n${CYAN}🗿 Moai Settings${NC}"
    echo "Choose how Moai faces are selected:"
    echo "1) Random (randomized faces)"
    echo "2) Sequential (cycle through all faces)"
    echo "3) Mood (try to match face to commit context)"
    read -p "Choose face selection mode (1-3): " face_choice
    echo
    
    case $face_choice in
        1)
            sed -i 's/"faces_mode": "random"/"faces_mode": "random"/g' "$CONFIG_FILE"
            ;;
        2)
            sed -i 's/"faces_mode": "random"/"faces_mode": "sequential"/g' "$CONFIG_FILE"
            ;;
        3)
            sed -i 's/"faces_mode": "random"/"faces_mode": "mood"/g' "$CONFIG_FILE"
            ;;
        *)
            # Default case, keep random
            ;;
    esac
    
    # Set ownership if running as sudo
    if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
        chown "$SUDO_USER" "$CONFIG_FILE"
    fi
    
    echo -e "${GREEN}✓${NC} Configuration saved to $CONFIG_FILE"
}

# Create scripts directory in the config directory
SCRIPTS_INSTALL_DIR="$CONFIG_DIR/scripts"
mkdir -p "$SCRIPTS_INSTALL_DIR"

# Copy scripts to the config directory
echo "Installing scripts to $SCRIPTS_INSTALL_DIR"
cp -r "$SCRIPT_DIR/scripts/"* "$SCRIPTS_INSTALL_DIR/" 2>/dev/null || true
# Ensure scripts are executable
chmod +x "$SCRIPTS_INSTALL_DIR/"*.sh "$SCRIPTS_INSTALL_DIR/prepare-commit-msg" 2>/dev/null || true

# If running as root, ensure the scripts are owned by the real user
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER" "$SCRIPTS_INSTALL_DIR"
fi

# Set up configuration interactively
setup_config

# Build the binary
echo "Building noidea..."
"$GO_CMD" build -o noidea

# Install the binary
echo "Installing noidea to $INSTALL_DIR"
cp noidea "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/noidea"

# Run the hook installation script if we're in a Git repository
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Detected Git repository, installing hooks..."
    
    # If we're running as root/sudo, run the script as the real user
    if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
        sudo -u "$SUDO_USER" "$SCRIPTS_INSTALL_DIR/install-hooks.sh"
    else
        "$SCRIPTS_INSTALL_DIR/install-hooks.sh"
    fi
else
    echo -e "${YELLOW}Not inside a Git repository, skipping hook installation${NC}"
    echo "You can install hooks later by running:"
    echo "  cd /path/to/your/repo && $INSTALL_DIR/noidea init"
fi

# Output success message
echo -e "${GREEN}✅ noidea has been successfully installed!${NC}"
echo ""

# Check if API key is set
if grep -q '"api_key": ""' "$CONFIG_DIR/config.json" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Important: No API key is configured.${NC}"
    echo "For the best experience with commit message suggestions,"
    echo "you need to set up an API key in your configuration:"
    echo ""
    echo "  Run: noidea config --init"
    echo "  Or edit: $CONFIG_DIR/config.json directly"
    echo ""
    echo "Without an API key, commit message suggestions will use a simple local algorithm"
    echo "that's less detailed than the AI-powered suggestions."
    echo ""
fi

echo "To use noidea in a Git repository:"
echo "  1. cd /path/to/your/repo"
echo "  2. noidea init                 # Set up Git hooks"
echo ""
echo "For commit message suggestions:"
echo "  noidea suggest                 # Run directly"
echo "  git config noidea.suggest true # Enable automatic suggestions"
echo ""
echo "For help and available commands:"
echo "  noidea --help"
echo ""

# Check if the installation directory is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}⚠️  Warning: $INSTALL_DIR is not in your PATH${NC}"
    echo "You might need to add it to your shell configuration:"
    echo ""
    echo "  For bash/zsh:"
    echo "    echo 'export PATH=\$PATH:$INSTALL_DIR' >> ~/.bashrc"
    echo "    # or"
    echo "    echo 'export PATH=\$PATH:$INSTALL_DIR' >> ~/.zshrc"
    echo ""
    echo "  For fish:"
    echo "    echo 'set -gx PATH \$PATH $INSTALL_DIR' >> ~/.config/fish/config.fish"
    echo ""
fi

echo -e "${BLUE}Thank you for installing noidea!${NC}" 