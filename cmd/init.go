package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/git"
)

var (
	enableSuggestions bool
	enableInteractive bool
	enableFullDiff    bool
	forceFlag         bool
)

func init() {
	initCmd.Flags().BoolVarP(&enableSuggestions, "suggest", "s", true, "Enable commit message suggestions")
	initCmd.Flags().BoolVarP(&enableInteractive, "interactive", "i", false, "Enable interactive mode for direct command usage")
	initCmd.Flags().BoolVarP(&enableFullDiff, "full-diff", "f", false, "Include full diffs in commit message analysis")
	initCmd.Flags().BoolVarP(&forceFlag, "force", "F", false, "Force installation even if checks fail")

	rootCmd.AddCommand(initCmd)
}

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize noidea in your Git repository",
	Long:  `Install the Git hooks for noidea in your repository, including Moai feedback and commit message suggestions.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Check if Git is installed
		if err := checkGitVersion(); err != nil {
			fmt.Println(color.RedString("Error:"), err)
			if !forceFlag {
				os.Exit(1)
			}
			fmt.Println(color.YellowString("Warning:"), "Continuing anyway due to --force flag")
		}

		// Check if we're in a Git repository
		gitDir, err := git.FindGitDir()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Not in a Git repository.")
			os.Exit(1)
		}

		// Create hooks directory if it doesn't exist
		hooksDir := filepath.Join(gitDir, "hooks")
		if err := os.MkdirAll(hooksDir, 0755); err != nil {
			fmt.Println(color.RedString("Error:"), "Failed to create hooks directory:", err)
			os.Exit(1)
		}

		// Check if hooks already exist and warn/backup if needed
		if !forceFlag {
			for _, hook := range []string{"post-commit", "prepare-commit-msg"} {
				hookPath := filepath.Join(hooksDir, hook)
				if _, err := os.Stat(hookPath); err == nil {
					// Hook exists, create backup
					backupPath := hookPath + ".bak"
					fmt.Println(color.YellowString("Warning:"), "Existing", hook, "hook found, creating backup at", backupPath)
					if err := os.Rename(hookPath, backupPath); err != nil {
						fmt.Println(color.RedString("Error:"), "Failed to backup existing hook:", err)
						fmt.Println("Use --force to override without backup")
						os.Exit(1)
					}
				}
			}
		}

		// Install the post-commit hook for Moai feedback
		err = git.InstallPostCommitHook(hooksDir)
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Failed to install post-commit hook:", err)
			os.Exit(1)
		}
		fmt.Println(color.GreenString("✓"), "Installed post-commit hook for Moai feedback")

		// Install the prepare-commit-msg hook for commit suggestions
		err = git.InstallPrepareCommitMsgHook(hooksDir)
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Failed to install prepare-commit-msg hook:", err)
			os.Exit(1)
		}
		fmt.Println(color.GreenString("✓"), "Installed prepare-commit-msg hook for commit suggestions")

		// Configure git settings based on flags
		gitConfigRunner := func(key, value string) error {
			cmd := exec.Command("git", "config", key, value)
			if out, err := cmd.CombinedOutput(); err != nil {
				return fmt.Errorf("git config failed: %w\nOutput: %s", err, out)
			}
			return nil
		}

		// Set suggestion configuration
		if err := gitConfigRunner("noidea.suggest", fmt.Sprintf("%t", enableSuggestions)); err != nil {
			fmt.Println(color.YellowString("Warning:"), "Failed to set git config:", err)
		}

		status := "enabled"
		if !enableSuggestions {
			status = "disabled"
		}
		fmt.Println(color.GreenString("✓"), "Commit message suggestions", status)

		// Only configure these if suggestions are enabled
		if enableSuggestions {
			if err := gitConfigRunner("noidea.suggest.interactive", fmt.Sprintf("%t", enableInteractive)); err != nil {
				fmt.Println(color.YellowString("Warning:"), "Failed to set interactive mode:", err)
			} else if enableInteractive {
				fmt.Println(color.GreenString("✓"), "Interactive mode enabled for direct command usage")
				fmt.Println(color.BlueString("Note:"), "Interactive mode only applies when running 'noidea suggest' directly.")
				fmt.Println("      Git hooks always use non-interactive mode to avoid input issues.")
			}

			if err := gitConfigRunner("noidea.suggest.full-diff", fmt.Sprintf("%t", enableFullDiff)); err != nil {
				fmt.Println(color.YellowString("Warning:"), "Failed to set full-diff mode:", err)
			} else if enableFullDiff {
				fmt.Println(color.GreenString("✓"), "Full diff analysis enabled")
			}
		}

		// Note: AI feedback is intentionally NOT integrated into git hooks.
		// Users can run `noidea moai --ai` manually when desired.


		// Check if noidea is properly available
		execPath, _ := os.Executable()
		fmt.Println(color.GreenString("Success!"), "noidea hooks installed - executable at:", execPath)
		fmt.Println(color.BlueString("Note:"), "To change settings, run 'git config noidea.suggest [true|false]'")

		// Load config and check if API key is set
		cfg := config.LoadConfig()
		if cfg.LLM.Enabled && cfg.LLM.APIKey == "" {
			fmt.Println()
			fmt.Println(color.YellowString("⚠️  Warning:"), "LLM is enabled but no API key is configured.")
			fmt.Println("     For better commit message suggestions, configure your API key:")
			fmt.Println("     Run 'noidea config --init' or edit ~/.noidea/config.json")
			fmt.Println()
			fmt.Println("     Without an API key, commit suggestions will use a simple local algorithm")
			fmt.Println("     that's less detailed than the AI-powered suggestions.")
		} else if !cfg.LLM.Enabled && enableSuggestions {
			fmt.Println()
			fmt.Println(color.BlueString("💡 Tip:"), "For better commit message suggestions, enable AI integration:")
			fmt.Println("     Run 'noidea config --init' to configure AI settings.")
		}

		// Final summary for smooth onboarding
		fmt.Println()
		fmt.Println(color.GreenString("🎉 noidea ready in this repo!"))
		fmt.Println(color.BlueString("Hooks installed:"))
		fmt.Println("  - prepare-commit-msg: Auto-suggests messages on 'git commit' (opens in editor)")
		fmt.Println("  - post-commit: Shows Moai face after commits")
		fmt.Println()
		fmt.Println(color.YellowString("Next: Try 'git commit' (no -m) for a suggestion!"))
		fmt.Println(color.BlueString("For AI-powered suggestions/feedback: 'noidea config --init'"))
		fmt.Println(color.BlueString("Toggle suggestions: 'git config noidea.suggest [true|false]'"))
		fmt.Println(color.BlueString("AI feedback: run 'noidea moai --ai' when you want it"))
	},
}

// checkGitVersion verifies Git is installed and meets minimum requirements
func checkGitVersion() error {
	// Check if git is available
	versionCmd := exec.Command("git", "--version")
	output, err := versionCmd.Output()
	if err != nil {
		return fmt.Errorf("git not found or not executable: %w", err)
	}

	// Parse git version (example output: "git version 2.34.1")
	versionStr := string(output)
	parts := strings.Fields(versionStr)
	if len(parts) < 3 {
		return fmt.Errorf("unexpected git version format: %s", versionStr)
	}

	// We could add version checking here if needed in the future
	// For now, just ensure git is available

	return nil
}
