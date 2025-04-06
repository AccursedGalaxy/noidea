package cmd

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/feedback"
	"github.com/AccursedGalaxy/noidea/internal/history"
	"github.com/AccursedGalaxy/noidea/internal/moai"
	"github.com/AccursedGalaxy/noidea/internal/personality"
)

var (
	// Flag to enable/disable AI feedback
	useAI bool
	// Flag to get the diff of the last commit
	includeDiff bool
	// Flag to set the personality
	personalityFlag string
	// Flag to list available personalities
	listPersonalities bool
	// Flag to include commit history context
	includeHistory bool
	// Flag to enable debug mode
	debugMode bool
)

func init() {
	rootCmd.AddCommand(moaiCmd)

	// Add flags
	moaiCmd.Flags().BoolVarP(&useAI, "ai", "a", false, "Use AI to generate feedback")
	moaiCmd.Flags().BoolVarP(&includeDiff, "diff", "d", false, "Include the diff in AI context")
	moaiCmd.Flags().StringVarP(&personalityFlag, "personality", "p", "", "Personality to use for feedback (default: from config)")
	moaiCmd.Flags().BoolVarP(&listPersonalities, "list-personalities", "l", false, "List available personalities")
	moaiCmd.Flags().BoolVarP(&includeHistory, "history", "H", false, "Include recent commit history context")
	moaiCmd.Flags().BoolVarP(&debugMode, "debug", "D", false, "Enable debug mode to show detailed API information")
}

var moaiCmd = &cobra.Command{
	Use:   "moai [commit message]",
	Short: "Display a Moai with feedback on your commit",
	Long:  `Show a Moai face and random feedback about your most recent commit.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Load configuration
		cfg := config.LoadConfig()

		// If list personalities flag is set, show personalities and exit
		if listPersonalities {
			showPersonalities(cfg.Moai.PersonalityFile)
			return
		}

		var commitMsg string
		var commitDiff string

		// If commit message was provided as args, use it
		if len(args) > 0 {
			commitMsg = strings.Join(args, " ")
		} else {
			// Otherwise, try to get the latest commit message
			gitCmd := exec.Command("git", "log", "-1", "--pretty=%B")
			output, err := gitCmd.Output()
			if err != nil {
				commitMsg = "unknown commit"
			} else {
				commitMsg = strings.TrimSpace(string(output))
			}
		}

		// If diff flag is set, get the diff too
		if includeDiff {
			gitCmd := exec.Command("git", "show", "--stat", "HEAD")
			output, err := gitCmd.Output()
			if err == nil {
				commitDiff = string(output)
			}
		}

		// Get the Moai face
		face := moai.GetRandomFace()

		// Override AI flag from config if set
		if !useAI && cfg.LLM.Enabled {
			useAI = true
		}

		// Get personality name, using flag if provided, otherwise from config
		personalityName := cfg.Moai.Personality
		if personalityFlag != "" {
			personalityName = personalityFlag
		}

		// Display the commit message with better formatting
		bold := color.New(color.Bold).SprintFunc()
		fmt.Printf("  %s  %s\n\n", color.HiMagentaString(face), bold(commitMsg))

		// Generate feedback based on AI flag
		if useAI {
			// Create commit context
			commitContext := feedback.CommitContext{
				Message:   commitMsg,
				Timestamp: time.Now(),
				Diff:      commitDiff,
			}

			// Add commit history context if requested
			if includeHistory {
				// Get commit history
				recentCommits, recentStats, err := getCommitHistoryContext()
				if err == nil && len(recentCommits) > 0 {
					commitContext.CommitHistory = recentCommits
					commitContext.CommitStats = recentStats
				}
			}

			// Create feedback engine based on configuration
			engine := feedback.NewFeedbackEngine(
				cfg.LLM.Provider,
				cfg.LLM.Model,
				cfg.LLM.APIKey,
				personalityName,
				cfg.Moai.PersonalityFile,
			)

			// Generate AI feedback
			fmt.Printf("  %s", color.HiBlackString("Generating AI feedback..."))
			aiResponse, err := engine.GenerateFeedback(commitContext)
			fmt.Print("\r\033[K") // Clear the "Generating" message

			if err != nil {
				// On error, fallback to local feedback
				feedbackMsg := moai.GetRandomFeedback(commitMsg)
				fmt.Printf("  %s\n\n", color.YellowString(feedbackMsg))
				fmt.Printf("  %s %v\n", color.New(color.FgRed, color.Bold).Sprint("❌ AI Error:"), err)

				// If debug mode is enabled, show more details
				if debugMode {
					fmt.Println("\n  " + color.New(color.FgCyan, color.Bold).Sprint("🔍 Debug information:"))
					fmt.Printf("    Provider: %s\n", color.CyanString(cfg.LLM.Provider))
					fmt.Printf("    Model: %s\n", color.CyanString(cfg.LLM.Model))
					apiKeyLength := 0
					if cfg.LLM.APIKey != "" {
						apiKeyLength = len(cfg.LLM.APIKey)
						fmt.Printf("    API key length: %s\n", color.CyanString(strconv.Itoa(apiKeyLength)))

						// Show a short prefix of the API key for debugging
						prefixLen := 10
						if apiKeyLength < prefixLen {
							prefixLen = apiKeyLength
						}
						fmt.Printf("    API key prefix: %s\n", color.CyanString(cfg.LLM.APIKey[:prefixLen]))
					} else {
						fmt.Printf("    API key length: %s (no API key found)\n", color.RedString("0"))
					}
				}
			} else {
				// Display AI-generated feedback with a box or indentation
				aiLines := strings.Split(aiResponse, "\n")
				fmt.Println()
				for _, line := range aiLines {
					if line != "" {
						fmt.Printf("  %s\n", color.New(color.FgCyan).Sprint(line))
					} else {
						fmt.Println()
					}
				}
				fmt.Println()
			}
		} else {
			// Use local feedback
			feedbackMsg := moai.GetRandomFeedback(commitMsg)
			fmt.Printf("  %s\n\n", color.YellowString(feedbackMsg))
		}
	},
}

// getCommitHistoryContext retrieves recent commit history for context
func getCommitHistoryContext() ([]string, map[string]interface{}, error) {
	// Get last 5 commits (not including current one)
	commits, err := history.GetLastNCommits(6, false)
	if err != nil || len(commits) <= 1 {
		return nil, nil, err
	}

	// Skip the most recent commit (it's the one we're currently giving feedback for)
	commits = commits[1:]

	// Extract messages
	messages := make([]string, len(commits))
	for i, commit := range commits {
		messages[i] = commit.Message
	}

	// Get stats
	collector, err := history.NewHistoryCollector()
	if err != nil {
		return messages, nil, err
	}

	stats := collector.CalculateStats(commits)

	return messages, stats, nil
}

// showPersonalities displays a list of available personalities
func showPersonalities(personalityFile string) {
	// Load personalities
	personalities, err := personality.LoadPersonalities(personalityFile)
	if err != nil {
		fmt.Println(color.RedString("Error loading personalities:"), err)
		return
	}

	fmt.Println(color.CyanString("🧠 Available personalities:"))
	fmt.Println()

	// Get default personality name
	defaultName := personalities.Default

	// Display all personalities
	for name, p := range personalities.Personalities {
		// Mark default with an asterisk
		defaultMarker := ""
		if name == defaultName {
			defaultMarker = color.GreenString(" (default)")
		}

		fmt.Printf("%s%s: %s\n", color.YellowString(name), defaultMarker, p.Description)
	}

	fmt.Println()
	fmt.Println("To use a specific personality:")
	fmt.Println("  noidea moai --ai --personality=<name>")
	fmt.Println()
	fmt.Println("To set a default personality:")
	fmt.Println("  export NOIDEA_PERSONALITY=<name>")
	fmt.Println("  or add to your .noidea.toml configuration file")
}
