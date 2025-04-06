package cmd

import (
	"bufio"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/secure"
)

// Version information
var (
	Version   = "v0.4.2" // Will be overridden during build
	BuildDate = "dev"    // Will be overridden during build
	Commit    = "none"   // Will be overridden during build
)

// Flag variables
var versionFlag bool

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "noidea",
	Short: "noidea - The Git Extension You Never Knew You Needed",
	Long: `🧠 noidea - A lightweight, plug-and-play Git extension that adds
✨fun and occasionally usefulfeedback into your normal Git workflow.

Every time you commit, a mysterious Moai appears to judge your code.

Main commands:
  suggest     Generate commit message suggestions based on staged changes
  moai        Show feedback about your most recent commit
  summary     Generate a summary of your recent Git activity
  init        Set up noidea in your Git repository
  config      Manage noidea configuration`,
	Run: func(cmd *cobra.Command, args []string) {
		// If version flag is set, print version and exit
		if versionFlag {
			printVersion()
			return
		}

		// If no subcommand is provided, print help
		cmd.Help()
	},
}

func init() {
	// Load environment variables from .env files
	loadEnvFiles()

	// Add version flag
	rootCmd.Flags().BoolVarP(&versionFlag, "version", "v", false, "Print version information and exit")

	// Check API key validity during startup, but only for certain commands
	cobra.OnInitialize(func() {
		// Only validate API key when using commands that need it
		if len(os.Args) > 1 {
			cmd := os.Args[1]
			// Only check for certain commands that need API key
			if cmd == "suggest" || cmd == "moai" || cmd == "summary" {
				// Check API key in background to avoid slowing down startup
				go validateApiKeyOnStartup()
			}
		}

		// Check for updates occasionally
		go checkForUpdatesInBackground()
	})
}

// loadEnvFiles loads environment variables from .env files in various locations
func loadEnvFiles() {
	// Try to find .env file in several locations
	locations := []string{
		".env",        // Current directory
		".noidea.env", // Alternative name in current directory
	}

	// Try to get home directory for additional locations
	if homeDir, err := os.UserHomeDir(); err == nil {
		locations = append(locations, filepath.Join(homeDir, ".noidea", ".env"))
	}

	// Note: .env files are being deprecated in favor of secure storage.
	// This is kept for backward compatibility.
	found := false

	for _, location := range locations {
		if _, err := os.Stat(location); err == nil {
			// File exists, try to load it
			file, err := os.Open(location)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Warning: Error opening %s: %v\n", location, err)
				continue
			}

			scanner := bufio.NewScanner(file)
			for scanner.Scan() {
				line := scanner.Text()

				// Skip empty lines and comments
				if line == "" || strings.HasPrefix(line, "#") {
					continue
				}

				// Split by first equals sign
				parts := strings.SplitN(line, "=", 2)
				if len(parts) != 2 {
					continue
				}

				key := strings.TrimSpace(parts[0])
				value := strings.TrimSpace(parts[1])

				// Remove quotes if present
				value = strings.Trim(value, `"'`)

				// Only set if not already in environment
				if _, exists := os.LookupEnv(key); !exists {
					os.Setenv(key, value)
				}
			}

			file.Close()
			found = true
			break // Successfully loaded one file, stop looking
		}
	}

	// If we loaded a .env file with API keys, print a deprecation warning
	if found {
		for _, key := range []string{"XAI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "NOIDEA_API_KEY"} {
			if val, exists := os.LookupEnv(key); exists && val != "" {
				fmt.Fprintf(os.Stderr, "Warning: Using API keys from .env files is deprecated and less secure.\n")
				fmt.Fprintf(os.Stderr, "Consider switching to secure storage with 'noidea config apikey'\n")
				break
			}
		}
	}
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	// This is a simple test comment to check commit message generation
	err := rootCmd.Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s %v\n", color.RedString("Error:"), err)
		os.Exit(1)
	}
}

// printVersion prints detailed version information
func printVersion() {
	bold := color.New(color.Bold).SprintFunc()
	cyan := color.New(color.FgCyan).SprintFunc()

	fmt.Printf("📦 %s %s\n", bold("noidea version:"), cyan(Version))
	fmt.Printf("🔨 %s %s\n", bold("Build date:"), cyan(BuildDate))
	fmt.Printf("🔖 %s %s\n", bold("Git commit:"), cyan(Commit))
}

// validateApiKeyOnStartup checks API key validity on startup and warns if there are issues
func validateApiKeyOnStartup() {
	// Load config to get API key and provider
	cfg := config.LoadConfig()

	// Only check if LLM is enabled and API key is set
	if cfg.LLM.Enabled && cfg.LLM.APIKey != "" {
		// Try to validate the API key
		isValid, err := secure.ValidateAPIKey(cfg.LLM.Provider, cfg.LLM.APIKey)
		if err != nil {
			yellow := color.New(color.FgYellow, color.Bold).SprintFunc()
			fmt.Fprintf(os.Stderr, "\n%s %v\n", yellow("⚠️  Warning:"), err)
			fmt.Fprintf(os.Stderr, "      You may want to check your API key with '%s'\n\n",
				color.CyanString("noidea config apikey-status"))
		} else if !isValid {
			red := color.New(color.FgRed, color.Bold).SprintFunc()
			fmt.Fprintf(os.Stderr, "\n%s Your API key for %s appears to be invalid.\n",
				red("❌ Warning:"), color.CyanString(cfg.LLM.Provider))
			fmt.Fprintf(os.Stderr, "      Please update it with '%s'\n\n",
				color.CyanString("noidea config apikey"))
		}
	}
}

// validateAPIKey checks if the API key works with the provider
func validateAPIKey(provider, apiKey string) (bool, error) {
	switch provider {
	case "xai":
		return validateXAIKey(apiKey)
	case "openai":
		return validateOpenAIKey(apiKey)
	case "deepseek":
		return validateDeepSeekKey(apiKey)
	default:
		return false, fmt.Errorf("unknown provider: %s", provider)
	}
}

// validateXAIKey checks if the xAI API key is valid
func validateXAIKey(apiKey string) (bool, error) {
	// Simple HTTP request to xAI API to verify key
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	req, err := http.NewRequest("GET", "https://api.groq.com/v1/models", nil)
	if err != nil {
		return false, err
	}

	req.Header.Add("Authorization", "Bearer "+apiKey)

	resp, err := client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	// Check if the request was successful
	return resp.StatusCode >= 200 && resp.StatusCode < 300, nil
}

// validateOpenAIKey checks if the OpenAI API key is valid
func validateOpenAIKey(apiKey string) (bool, error) {
	// Simple HTTP request to OpenAI API to verify key
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	req, err := http.NewRequest("GET", "https://api.openai.com/v1/models", nil)
	if err != nil {
		return false, err
	}

	req.Header.Add("Authorization", "Bearer "+apiKey)

	resp, err := client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	// Check if the request was successful
	return resp.StatusCode >= 200 && resp.StatusCode < 300, nil
}

// validateDeepSeekKey checks if the DeepSeek API key is valid
func validateDeepSeekKey(apiKey string) (bool, error) {
	// Simple HTTP request to DeepSeek API to verify key
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	req, err := http.NewRequest("GET", "https://api.deepseek.com/v1/models", nil)
	if err != nil {
		return false, err
	}

	req.Header.Add("Authorization", "Bearer "+apiKey)

	resp, err := client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	// Check if the request was successful
	return resp.StatusCode >= 200 && resp.StatusCode < 300, nil
}

// checkForUpdatesInBackground checks for noidea updates periodically
func checkForUpdatesInBackground() {
	// Skip update check if in dev mode
	if BuildDate == "dev" || strings.Contains(Version, "dev") {
		return
	}

	// Only check for updates occasionally (every ~10 commands)
	// Use a simple heuristic based on timestamp in update file
	lastCheckedFile := getUpdateCheckFilePath()
	shouldCheck, _ := shouldCheckForUpdates(lastCheckedFile)
	if !shouldCheck {
		return
	}

	// Check latest version from GitHub (quietly)
	latestVersion, _, err := getLatestVersionFromGitHub()
	if err != nil {
		// Silently fail on error
		return
	}

	// Compare versions
	currentVersion := strings.TrimPrefix(Version, "v")
	latestVersionStr := strings.TrimPrefix(latestVersion, "v")

	// Only notify if using an older version
	if isNewerVersion(latestVersionStr, currentVersion) {
		// Update the last checked file regardless of result
		updateLastCheckedFile(lastCheckedFile)

		// Print update notification
		fmt.Println()
		fmt.Println(color.YellowString("🔔 Update available!"))
		fmt.Printf("A new version of noidea is available: %s → %s\n", Version, latestVersion)
		fmt.Println("To update, run: noidea update")
		fmt.Println()
	}
}

// shouldCheckForUpdates determines if we should check for updates
func shouldCheckForUpdates(filePath string) (bool, error) {
	// If file doesn't exist, create it and return true
	info, err := os.Stat(filePath)
	if os.IsNotExist(err) {
		return true, nil
	}
	if err != nil {
		return false, err
	}

	// Check if file is older than 24 hours
	modTime := info.ModTime()
	return time.Since(modTime) > 24*time.Hour, nil
}

// updateLastCheckedFile updates the timestamp of the update check file
func updateLastCheckedFile(filePath string) {
	// Create directory if it doesn't exist
	dir := filepath.Dir(filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return
	}

	// Create or touch the file
	file, err := os.Create(filePath)
	if err != nil {
		return
	}
	defer file.Close()
}

// getUpdateCheckFilePath returns the path to the update check file
func getUpdateCheckFilePath() string {
	// Get the user's config directory
	configDir, err := os.UserConfigDir()
	if err != nil {
		// Fallback to home directory
		home, err := os.UserHomeDir()
		if err != nil {
			// Last resort, use temp directory
			return filepath.Join(os.TempDir(), ".noidea_update_check")
		}
		return filepath.Join(home, ".noidea", ".update_check")
	}
	return filepath.Join(configDir, "noidea", ".update_check")
}

// isNewerVersion compares two version strings
func isNewerVersion(latest, current string) bool {
	// If versions are identical, latest is not newer
	if latest == current {
		return false
	}

	// Handle development versions (e.g., v0.4.0-11-g9839b73)
	// If current has a dash but latest doesn't, current is a dev version
	// based on the latest version and therefore is newer
	if strings.Contains(current, "-") && !strings.Contains(latest, "-") {
		// Get the base version before the dash
		currentBase := strings.Split(current, "-")[0]

		// If the base version is the same as latest, the dev version is newer
		if currentBase == latest {
			return false // latest is NOT newer
		}
	}

	// Strip non-semver parts for clean comparison
	latestClean := strings.Split(latest, "-")[0]
	currentClean := strings.Split(current, "-")[0]

	// Convert version strings to comparable slices
	latestParts := strings.Split(latestClean, ".")
	currentParts := strings.Split(currentClean, ".")

	// Make sure both slices have the same length
	for len(latestParts) < 3 {
		latestParts = append(latestParts, "0")
	}
	for len(currentParts) < 3 {
		currentParts = append(currentParts, "0")
	}

	// Compare major, minor, and patch versions
	for i := 0; i < 3; i++ {
		latestNum := 0
		currentNum := 0
		fmt.Sscanf(latestParts[i], "%d", &latestNum)
		fmt.Sscanf(currentParts[i], "%d", &currentNum)

		if latestNum > currentNum {
			return true // latest is newer
		}
		if latestNum < currentNum {
			return false // latest is older
		}
	}

	return false // versions are equal in their numeric parts
}
