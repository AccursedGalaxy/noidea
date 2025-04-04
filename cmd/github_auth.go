package cmd

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/AccursedGalaxy/noidea/internal/github"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"golang.org/x/term"
)

func init() {
	// Add GitHub auth commands to config command
	configCmd.AddCommand(configGitHubAuthCmd)
	configCmd.AddCommand(configGitHubAuthStatusCmd)
}

var configGitHubAuthCmd = &cobra.Command{
	Use:   "github-auth",
	Short: "Configure GitHub authentication",
	Long:  `Configure GitHub authentication for issue management and other API features.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(color.CyanString("GitHub Authentication Setup"))
		fmt.Println("This will configure your GitHub authentication for issue management and other API features.")
		fmt.Println()
		
		// Check if GitHub CLI is installed and use it if available
		if hasGitHubCLI() {
			fmt.Println(color.YellowString("GitHub CLI detected!"))
			fmt.Print("Would you like to use GitHub CLI for authentication? [Y/n]: ")
			
			reader := bufio.NewReader(os.Stdin)
			answer, _ := reader.ReadString('\n')
			answer = strings.TrimSpace(strings.ToLower(answer))
			
			if answer != "n" && answer != "no" {
				fmt.Println(color.CyanString("Using GitHub CLI for authentication..."))
				if configureWithGitHubCLI() {
					return
				}
			}
		}
		
		// Token setup
		fmt.Println("\nPlease create a Personal Access Token at: https://github.com/settings/tokens/new")
		fmt.Println("Token needs at least 'repo' scope for GitHub issue integration.")
		fmt.Println()
		
		// Read token from user
		token := readSecureInput("Enter your GitHub token: ")
		if token == "" {
			fmt.Println(color.RedString("Error:"), "Token cannot be empty")
			return
		}
		
		// Validate and store token
		auth := github.NewAuthenticator()
		valid, err := auth.ValidateToken(token)
		if err != nil || !valid {
			fmt.Println(color.RedString("Error:"), "Invalid token:", err)
			return
		}
		
		if err := auth.SetToken(token); err != nil {
			fmt.Println(color.RedString("Error:"), "Failed to store token:", err)
			return
		}
		
		// Get authenticated user to verify and display
		user, err := auth.GetAuthenticatedUser()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Failed to get user information:", err)
			return
		}
		
		fmt.Println(color.GreenString("\nAuthentication successful!"))
		fmt.Println("Authenticated as:", color.YellowString(user))
	},
}

var configGitHubAuthStatusCmd = &cobra.Command{
	Use:   "github-auth-status",
	Short: "Check GitHub authentication status",
	Long:  `Check if GitHub authentication is configured and working.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Create authenticator
		auth := github.NewAuthenticator()
		
		// Try to get token
		token, err := auth.GetToken()
		if err != nil {
			fmt.Println(color.RedString("Not authenticated with GitHub"))
			fmt.Println("Run 'noidea config github-auth' to set up authentication")
			return
		}
		
		// Validate token
		valid, err := auth.ValidateToken(token)
		if err != nil || !valid {
			fmt.Println(color.RedString("GitHub token is invalid or expired"))
			fmt.Println("Run 'noidea config github-auth' to set up authentication")
			return
		}
		
		// Get authenticated user
		user, err := auth.GetAuthenticatedUser()
		if err != nil {
			fmt.Println(color.RedString("Failed to get user information:"), err)
			return
		}
		
		fmt.Println(color.GreenString("Authenticated with GitHub using token"))
		fmt.Println("User:", color.YellowString(user))
		
		// Show masked token
		maskedToken := maskToken(token)
		fmt.Println("Token:", maskedToken)
	},
}

// hasGitHubCLI checks if the GitHub CLI is installed
func hasGitHubCLI() bool {
	cmd := exec.Command("gh", "--version")
	return cmd.Run() == nil
}

// configureWithGitHubCLI uses the GitHub CLI to get a token
func configureWithGitHubCLI() bool {
	// Check if already logged in
	cmd := exec.Command("gh", "auth", "status")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Println(color.RedString("GitHub CLI not authenticated. Please run 'gh auth login' first."))
		return false
	}
	
	fmt.Println(string(output))
	
	// Get token from GitHub CLI
	cmd = exec.Command("gh", "auth", "token")
	tokenBytes, err := cmd.Output()
	if err != nil {
		fmt.Println(color.RedString("Error:"), "Failed to get token from GitHub CLI:", err)
		return false
	}
	
	token := strings.TrimSpace(string(tokenBytes))
	if token == "" {
		fmt.Println(color.RedString("Error:"), "Empty token received from GitHub CLI")
		return false
	}
	
	// Store token
	auth := github.NewAuthenticator()
	if err := auth.SetToken(token); err != nil {
		fmt.Println(color.RedString("Error:"), "Failed to store token:", err)
		return false
	}
	
	// Get authenticated user
	user, err := auth.GetAuthenticatedUser()
	if err != nil {
		fmt.Println(color.RedString("Error:"), "Failed to get user information:", err)
		return false
	}
	
	fmt.Println(color.GreenString("\nAuthentication successful!"))
	fmt.Println("Authenticated as:", color.YellowString(user))
	return true
}

// readSecureInput reads a password from stdin without echoing
func readSecureInput(prompt string) string {
	fmt.Print(prompt)
	
	// Use term.ReadPassword for secure input when possible
	if fileInfo, _ := os.Stdin.Stat(); (fileInfo.Mode() & os.ModeCharDevice) != 0 {
		password, err := term.ReadPassword(int(os.Stdin.Fd()))
		fmt.Println() // Add newline after input
		if err != nil {
			// Fallback to regular input
			reader := bufio.NewReader(os.Stdin)
			text, _ := reader.ReadString('\n')
			return strings.TrimSpace(text)
		}
		return strings.TrimSpace(string(password))
	}
	
	// Fallback for non-terminal input
	reader := bufio.NewReader(os.Stdin)
	text, _ := reader.ReadString('\n')
	return strings.TrimSpace(text)
}

// maskToken masks a token for display
func maskToken(token string) string {
	if len(token) <= 8 {
		return "****"
	}
	
	return token[:4] + "..." + token[len(token)-4:]
} 