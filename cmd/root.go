package cmd

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/secure"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

// Version information
var (
	Version   = "v0.2.3" // Will be overridden during build
	BuildDate = "dev"   // Will be overridden during build
	Commit    = "none"  // Will be overridden during build
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
	})
}

// loadEnvFiles loads environment variables from .env files in various locations
func loadEnvFiles() {
	// Try to find .env file in several locations
	locations := []string{
		".env",                              // Current directory
		".noidea.env",                       // Alternative name in current directory
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
		fmt.Println(color.RedString("Error:"), err)
		os.Exit(1)
	}
}

// printVersion prints detailed version information
func printVersion() {
	fmt.Printf("noidea version %s\n", Version)
	fmt.Printf("Build date: %s\n", BuildDate)
	fmt.Printf("Git commit: %s\n", Commit)
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
			fmt.Fprintf(os.Stderr, "\n%s API key validation error: %v\n", color.YellowString("Warning:"), err)
			fmt.Fprintf(os.Stderr, "You may want to check your API key with 'noidea config apikey-status'\n\n")
		} else if !isValid {
			fmt.Fprintf(os.Stderr, "\n%s Your API key for %s appears to be invalid.\n", 
				color.RedString("Warning:"), cfg.LLM.Provider)
			fmt.Fprintf(os.Stderr, "Please update it with 'noidea config apikey'\n\n")
		}
	}
}