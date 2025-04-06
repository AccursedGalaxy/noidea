package cmd

// suggest.go - Commit message suggestion functionality
//
// This file implements the 'suggest' command for generating conventional commit messages.
// Conventional commit format follows the pattern: <type>[(scope)]: <description>
//
// Common types include:
// - feat: A new feature
// - fix: A bug fix
// - docs: Documentation changes
// - style: Code style changes (formatting, etc)
// - refactor: Code changes that neither fix bugs nor add features
// - test: Adding or fixing tests
// - chore: Maintenance tasks, dependencies, etc
//
// Example: feat(auth): implement password reset functionality

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"golang.org/x/term"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/feedback"
	"github.com/AccursedGalaxy/noidea/internal/history"
)

var (
	// Suggest command flags
	historyCountFlag  int
	fullDiffFlag      bool
	interactiveFlag   bool
	commitMsgFileFlag string
	quietFlag         bool // Flag for machine-readable output without UI elements

	// Add divider constant here, grouped with other constants
	divider = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
)

func init() {
	rootCmd.AddCommand(suggestCmd)

	// Add flags
	suggestCmd.Flags().IntVarP(&historyCountFlag, "history", "n", 10, "Number of recent commits to analyze for context")
	suggestCmd.Flags().BoolVarP(&fullDiffFlag, "full-diff", "f", false, "Include full diff instead of summary")
	suggestCmd.Flags().BoolVarP(&interactiveFlag, "interactive", "i", false, "Interactive mode to approve/reject suggestions")
	suggestCmd.Flags().StringVarP(&commitMsgFileFlag, "file", "F", "", "Path to commit message file (for prepare-commit-msg hook)")
	suggestCmd.Flags().BoolVarP(&quietFlag, "quiet", "q", false, "Output only the message without UI elements (for scripts)")
}

// suggestCmd represents the suggest command
var suggestCmd = &cobra.Command{
	Use:   "suggest",
	Short: "Suggest a commit message for staged changes",
	Long: `Generates an AI-suggested commit message based on your staged git changes.
This provides a good starting point for your commits.

Example:
  noidea suggest                  # Get a commit message suggestion
  noidea suggest -p coder         # Get a suggestion using the "coder" personality
  noidea suggest -p silly         # Get a suggestion with a silly personality
  noidea suggest | git commit -F- # Pipe suggestion directly into git commit
  git noidea suggest              # Use the git extension (if installed)`,
	// Added this comment to test the improved commit message generation algorithm
	Run: func(cmd *cobra.Command, args []string) {
		// Load configuration
		cfg := config.LoadConfig()

		// Get staged changes
		diff, err := getStagedDiff()
		if err != nil {
			fmt.Println(color.RedString("❌ Error:"), "Failed to get staged changes:", err)
			return
		}

		// Check if there are staged changes
		if strings.TrimSpace(diff) == "" {
			fmt.Println(color.YellowString("⚠️ No staged changes found. Stage files with 'git add' first."))
			return
		}

		// Get recent commit history for context
		commits, err := history.GetLastNCommits(historyCountFlag, false)
		if err != nil {
			fmt.Println(color.YellowString("⚠️ Warning:"), "Failed to get commit history. Continuing with staged changes only.")
		}

		// Extract commit messages and stats
		var commitMessages []string
		for _, commit := range commits {
			commitMessages = append(commitMessages, commit.Message)
		}

		// Create a history collector to calculate stats
		collector, _ := history.NewHistoryCollector()
		stats := collector.CalculateStats(commits)

		// Create feedback engine based on config
		engineProvider := cfg.LLM.Provider
		engineModel := cfg.LLM.Model
		apiKey := cfg.LLM.APIKey
		personality := cfg.Moai.Personality
		personalityFile := cfg.Moai.PersonalityFile

		engine := feedback.NewFeedbackEngine(engineProvider, engineModel, apiKey, personality, personalityFile)

		// Create commit context for the suggestion
		ctx := feedback.CommitContext{
			Diff:          diff,
			CommitHistory: commitMessages,
			CommitStats:   stats,
			Timestamp:     time.Now(),
		}

		// If fullDiffFlag is true, provide the entire diff, otherwise summarize
		if !fullDiffFlag {
			// Create a summarized version of the diff for conciseness
			ctx.Diff = summarizeDiff(diff)
		}

		// Get width of terminal
		width := 80
		if w, _, err := term.GetSize(0); err == nil && w > 0 {
			width = w
		}

		// Print a header with divider
		fmt.Println()
		fmt.Println(color.New(color.Bold).Sprintf("🔮 Commit Message Suggestion"))
		fmt.Println(color.HiBlackString(strings.Repeat("━", width/2)))

		// Print analysis info with spinner-like prefix
		fmt.Printf("  %s %s %s\n",
			color.HiMagentaString("◉"),
			color.New(color.Bold).Sprintf("Analyzing:"),
			color.CyanString("staged changes and %d recent commits", len(commitMessages)))

		// Progress indication
		fmt.Printf("  %s %s\n",
			color.HiBlueString("◉"),
			color.New(color.Bold).Sprintf("Generating commit message..."))

		// If using full diff, indicate that we're doing detailed code analysis
		if fullDiffFlag {
			fmt.Printf("  %s %s\n",
				color.HiCyanString("◉"),
				color.New(color.Bold).Sprintf("Performing detailed code analysis"))
		}

		// Generate suggested commit message
		suggestion, err := engine.GenerateCommitSuggestion(ctx)
		if err != nil {
			fmt.Println(color.RedString("❌ Error:"), "Failed to generate suggestion:", err)
			return
		}

		// Handle output based on flags
		if quietFlag {
			// For quiet mode, just handle the commit message file without any UI
			if commitMsgFileFlag != "" {
				err := writeToCommitMsgFile(suggestion, commitMsgFileFlag)
				if err != nil {
					fmt.Println(color.RedString("❌ Error:"), "Failed to write commit message:", err)
					return
				}
			} else {
				// Just print the raw message for piping
				fmt.Print(suggestion)
			}
		} else {
			// Standard output with UI elements
			fmt.Println()
			fmt.Println(color.New(color.Bold).Sprintf("✨ Suggested Commit Message"))
			fmt.Println(color.HiBlackString(strings.Repeat("━", width/2)))

			if interactiveFlag {
				// Handle interactive mode
				handleInteractiveMode(suggestion, commitMsgFileFlag)
			} else {
				// Check if we're being called from a git hook (via --file flag)
				isFromGitHook := commitMsgFileFlag != ""

				// Only print the message preview when NOT called from a git hook
				// or if called directly by the user
				if !isFromGitHook {
					// Handle multi-line commit messages with better formatting
					lines := strings.Split(suggestion, "\n")
					if len(lines) > 1 {
						// Print the first line (subject) in bold cyan
						fmt.Println(color.New(color.FgHiCyan, color.Bold).Sprintf("  %s", lines[0]))
						fmt.Println()

						// Print the rest with proper formatting
						for i := 1; i < len(lines); i++ {
							if lines[i] == "" {
								// Print empty lines as is
								fmt.Println()
							} else {
								// Print content lines indented
								fmt.Println(color.CyanString("  %s", lines[i]))
							}
						}
					} else {
						// Single line message
						fmt.Println(color.New(color.FgHiCyan, color.Bold).Sprintf("  %s", suggestion))
					}

					fmt.Println()
					fmt.Println(color.HiBlackString("  To use: ") + color.WhiteString("git commit -m \"") +
						color.HiCyanString("%s", suggestion) + color.WhiteString("\""))
				}
			}
		}
	},
}

// getStagedDiff gets the diff of staged changes
func getStagedDiff() (string, error) {
	// Use a more efficient approach with custom buffer sizing
	cmd := exec.Command("git", "diff", "--staged")

	// Create a buffer with reasonable initial size to reduce allocations
	var outputBuffer strings.Builder
	outputBuffer.Grow(8192) // Pre-allocate 8KB which is sufficient for most diffs

	// Setup command to write directly to our buffer
	cmd.Stdout = &outputBuffer

	// Run the command
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("failed to get staged diff: %w", err)
	}

	return outputBuffer.String(), nil
}

// summarizeDiff creates a concise version of the diff
// It keeps file headers and a limited number of changed lines per file
func summarizeDiff(diff string) string {
	const maxLinesPerFile = 50 // Maximum number of diff lines to show per file

	// If the diff is small enough, just return it
	lines := strings.Split(diff, "\n")
	if len(lines) <= maxLinesPerFile*2 {
		return diff
	}

	var result strings.Builder
	linesInCurrentFile := 0
	inFile := false

	for _, line := range lines {
		// Always include file headers and chunk headers
		if strings.HasPrefix(line, "diff --git") {
			// If we were in a file and truncated it, add an indicator
			if inFile && linesInCurrentFile >= maxLinesPerFile {
				result.WriteString("... (additional lines omitted for brevity) ...\n\n")
			}

			// Reset for the next file
			linesInCurrentFile = 0
			inFile = true

			// Add the file header
			result.WriteString(line + "\n")
		} else if strings.HasPrefix(line, "index ") ||
			strings.HasPrefix(line, "---") ||
			strings.HasPrefix(line, "+++") ||
			strings.HasPrefix(line, "@@") {
			// Always include these git metadata lines
			result.WriteString(line + "\n")
		} else if linesInCurrentFile < maxLinesPerFile {
			// Include the line if we haven't hit the max for this file
			result.WriteString(line + "\n")
			linesInCurrentFile++
		}
	}

	// Add a final truncation notice if needed
	if inFile && linesInCurrentFile >= maxLinesPerFile {
		result.WriteString("... (additional lines omitted for brevity) ...\n")
	}

	return result.String()
}

// handleInteractiveMode presents the suggestion to the user and allows interaction
func handleInteractiveMode(suggestion string, commitMsgFileFlag string) {
	fmt.Println(color.GreenString("✨ Suggested commit message:"))

	// Handle multi-line commit messages with better formatting
	lines := strings.Split(suggestion, "\n")
	if len(lines) > 1 {
		// Print the first line (subject) in white
		fmt.Println(color.HiWhiteString(lines[0]))

		// Print the rest with proper formatting
		for i := 1; i < len(lines); i++ {
			if lines[i] == "" {
				// Print empty lines as is
				fmt.Println()
			} else {
				// Print content lines in white but not highlighted
				fmt.Println(color.WhiteString(lines[i]))
			}
		}
	} else {
		// Single line message
		fmt.Println(color.HiWhiteString(suggestion))
	}

	fmt.Println(color.HiBlackString(divider))

	// Ask if the user wants to use this suggestion
	fmt.Print(color.YellowString("Accept this suggestion? (Y/n/e): "))
	reader := bufio.NewReader(os.Stdin)
	response, _ := reader.ReadString('\n')
	response = strings.ToLower(strings.TrimSpace(response))

	// Default to yes if empty
	if response == "" || response == "y" || response == "yes" {
		if commitMsgFileFlag != "" {
			err := writeToCommitMsgFile(suggestion, commitMsgFileFlag)
			if err != nil {
				fmt.Println(color.RedString("❌ Error:"), "Failed to write commit message:", err)
				return
			}
			fmt.Println(color.GreenString("✅ Commit message accepted and applied"))
		} else {
			fmt.Println(color.GreenString("✅ Commit message accepted"))
			// Print to stdout for piping
			fmt.Println(suggestion)
		}
	} else if response == "e" || response == "edit" {
		editedMsg := editSuggestion(suggestion)
		if commitMsgFileFlag != "" {
			err := writeToCommitMsgFile(editedMsg, commitMsgFileFlag)
			if err != nil {
				fmt.Println(color.RedString("❌ Error:"), "Failed to write commit message:", err)
				return
			}
			fmt.Println(color.GreenString("✅ Edited commit message applied"))
		} else {
			fmt.Println(color.GreenString("✅ Commit message edited"))
			// Print to stdout for piping
			fmt.Println(editedMsg)
		}
	} else {
		fmt.Println(color.YellowString("Suggestion declined"))
	}
}

// writeToCommitMsgFile writes the commit message to the specified file
func writeToCommitMsgFile(message string, filePath string) error {
	// Verify file exists before attempting to write
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return fmt.Errorf("commit message file does not exist: %s", filePath)
	}

	// Open file with proper error handling
	file, err := os.OpenFile(filePath, os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return fmt.Errorf("failed to open commit message file: %w", err)
	}
	defer file.Close()

	// Write message with error handling
	if _, err := file.WriteString(message); err != nil {
		return fmt.Errorf("failed to write to commit message file: %w", err)
	}

	return nil
}

// editSuggestion allows the user to edit the suggested commit message
func editSuggestion(suggestion string) string {
	fmt.Println(color.CyanString("✏️ Current suggestion:"))
	fmt.Println(suggestion)
	fmt.Println(color.CyanString("Enter your edited message (type 'done' on a new line when finished):"))

	var lines []string
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "done" {
			break
		}
		lines = append(lines, line)
	}

	return strings.Join(lines, "\n")
}
