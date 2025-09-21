package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"golang.org/x/term"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/feedback"
	"github.com/AccursedGalaxy/noidea/internal/history"
	"github.com/AccursedGalaxy/noidea/internal/personality"
)

var (
	// Summary command flags
	daysFlag              int
	allHistoryFlag        bool
	exportFlag            string
	statsOnlyFlag         bool
	aiInsightFlag         bool
	personalityForSummary string
	showCommitHistoryFlag bool
)

func init() {
	rootCmd.AddCommand(summaryCmd)

	// Add flags
	summaryCmd.Flags().IntVarP(&daysFlag, "days", "d", 7, "Number of days to include in summary (default: 7, use 0 for all history)")
	summaryCmd.Flags().BoolVarP(&allHistoryFlag, "all", "A", false, "Show complete repository history regardless of --days value")
	summaryCmd.Flags().StringVarP(&exportFlag, "export", "e", "", "Export format: text, markdown, or html")
	summaryCmd.Flags().BoolVarP(&statsOnlyFlag, "stats-only", "s", false, "Show only statistics without AI insights")
	summaryCmd.Flags().BoolVarP(&aiInsightFlag, "ai", "a", false, "Include AI insights (default: use config)")
	summaryCmd.Flags().StringVarP(&personalityForSummary, "personality", "p", "", "Personality to use for insights (default: from config)")
	summaryCmd.Flags().BoolVarP(&showCommitHistoryFlag, "show-commits", "c", false, "Include detailed commit history in the output")
}

var summaryCmd = &cobra.Command{
	Use:   "summary",
	Short: "Generate a summary of recent Git activity",
	Long: `Analyze your Git history and provide statistics and insights about your recent commits.

By default, this command shows commits from the last 7 days. If no commits are found
in this period, it automatically shows all repository history.

Examples:
  noidea summary                # Show commits from the last 7 days
  noidea summary --days 30      # Show commits from the last 30 days
  noidea summary --all          # Show all repository history
  noidea summary --days 0       # Same as --all, shows all history
  noidea summary --show-commits # Include detailed commit history in output`,
	Run: func(cmd *cobra.Command, args []string) {
		// Load configuration
		cfg := config.LoadConfig()

		// Determine whether to use AI
		useAI := !statsOnlyFlag && (aiInsightFlag || cfg.LLM.Enabled)

		// Get personality name
		personalityName := cfg.Moai.Personality
		if personalityForSummary != "" {
			personalityName = personalityForSummary
		}

		var commits []history.CommitInfo
		var err error

		// Check if user requested all history
		if allHistoryFlag || daysFlag == 0 {
			// Fetch all commits
			commits, err = history.GetLastNCommits(1000, useAI)
			if err != nil {
				fmt.Println(color.RedString("Error:"), "Failed to retrieve commit history:", err)
				return
			}
			// Set days to a large value to indicate complete history in the summary
			daysFlag = 365 * 10 // 10 years, arbitrary large number
		} else {
			// Get commit data for the specified period
			commits, err = history.GetCommitsFromLastNDays(daysFlag, useAI)
			if err != nil {
				fmt.Println(color.RedString("Error:"), "Failed to retrieve commit history:", err)
				return
			}

			// Only show the fallback message and fetch all history if we truly have zero commits
			if len(commits) == 0 {
				// No commits in the specified time period, automatically fetch all history
				fmt.Println(color.YellowString("No commits found in the last"),
					color.CyanString(strconv.Itoa(daysFlag)),
					color.YellowString("days. Showing complete history instead."))

				// Get all commits by using GetLastNCommits with a high number
				commits, err = history.GetLastNCommits(1000, useAI)
				if err != nil {
					fmt.Println(color.RedString("Error:"), "Failed to retrieve commit history:", err)
					return
				}

				// Set days to a large value to indicate complete history in the summary
				daysFlag = 365 * 10 // 10 years, arbitrary large number
			}
		}

		// Use a direct Git command to get commits as a test
		if len(commits) == 0 {
			// Execute a direct Git command to see if we can get commits
			cmd := exec.Command("git", "log", "--pretty=format:%s", "-n", "10")
			out, err := cmd.Output()
			if err == nil && len(out) > 0 {
				// We got direct git output but no commits from our history function
				fmt.Println(color.YellowString("Warning:"), "Git history is available but our history collector couldn't retrieve it.")
				fmt.Println(color.YellowString("Recent commits from Git:"))
				fmt.Println(string(out))
			}
		}

		// Check if we have any commits after all attempts
		if len(commits) == 0 {
			fmt.Println(color.YellowString("No commits found in this repository."))
			return
		}

		// If showing all history, update the days value to reflect the actual time span
		if daysFlag >= 365*10 && len(commits) > 0 {
			// Find the oldest commit timestamp
			oldestCommit := commits[len(commits)-1].Timestamp
			days := int(time.Since(oldestCommit).Hours()/24) + 1

			// Only update if it's less than our arbitrary large number
			if days < 365*10 {
				daysFlag = days
			}
		}

		// Generate statistics
		// Directly get Git stats if collector doesn't provide data
		collector, err := history.NewHistoryCollector()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Failed to create history collector:", err)
			return
		}
		stats := collector.CalculateStats(commits)

		// Verify stats are not all zero
		allZeros := true
		if val, ok := stats["totalCommits"]; ok && val != nil {
			if v, ok := val.(int); ok && v > 0 {
				allZeros = false
			}
		}

		// If stats appear to be all zeros but we have commits, try to get stats directly
		if allZeros && len(commits) > 0 {
			// Directly calculate basic stats
			stats["totalCommits"] = len(commits)

			// Calculate unique authors
			authors := make(map[string]bool)
			for _, commit := range commits {
				authors[commit.Author] = true
			}
			stats["uniqueAuthors"] = len(authors)

			// Calculate timespan in hours
			if len(commits) >= 2 {
				newest := commits[0].Timestamp
				oldest := commits[len(commits)-1].Timestamp
				timeSpan := newest.Sub(oldest).Hours()
				stats["timeSpan"] = fmt.Sprintf("%.1f", timeSpan)
			} else {
				stats["timeSpan"] = "0.0"
			}

			// Calculate commits by day
			commitsByDay := make(map[string]int)
			for _, commit := range commits {
				day := commit.Timestamp.Weekday().String()
				commitsByDay[day]++
			}
			stats["commitsByDay"] = commitsByDay

			// Calculate commits by hour range
			commitsByHourRange := make(map[string]int)
			for _, commit := range commits {
				hour := commit.Timestamp.Hour()
				var hourRange string

				switch {
				case hour >= 4 && hour < 8:
					hourRange = "Morning (4-8)"
				case hour >= 8 && hour < 12:
					hourRange = "Work Hours (8-12)"
				case hour >= 12 && hour < 16:
					hourRange = "Afternoon (12-16)"
				case hour >= 16 && hour < 20:
					hourRange = "Evening (16-20)"
				case hour >= 20 && hour < 24:
					hourRange = "Late PM (20-24)"
				default:
					hourRange = "Night (0-4)"
				}

				commitsByHourRange[hourRange]++
			}
			stats["commitsByHourRange"] = commitsByHourRange

			// Try to get file stats using git command
			cmd := exec.Command("git", "diff", "--shortstat", commits[len(commits)-1].Hash, commits[0].Hash)
			out, err := cmd.Output()
			if err == nil {
				// Parse output like: " 10 files changed, 100 insertions(+), 50 deletions(-)"
				statStr := string(out)
				filesRe := regexp.MustCompile(`(\d+) files? changed`)
				addRe := regexp.MustCompile(`(\d+) insertions?\(\+\)`)
				delRe := regexp.MustCompile(`(\d+) deletions?\(-\)`)

				if matches := filesRe.FindStringSubmatch(statStr); len(matches) > 1 {
					if val, err := strconv.Atoi(matches[1]); err == nil {
						stats["filesChanged"] = val
					}
				}

				if matches := addRe.FindStringSubmatch(statStr); len(matches) > 1 {
					if val, err := strconv.Atoi(matches[1]); err == nil {
						stats["linesAdded"] = val
					}
				}

				if matches := delRe.FindStringSubmatch(statStr); len(matches) > 1 {
					if val, err := strconv.Atoi(matches[1]); err == nil {
						stats["linesRemoved"] = val
					}
				}

				// Calculate net change
				added := 0
				if val, ok := stats["linesAdded"].(int); ok {
					added = val
				}

				removed := 0
				if val, ok := stats["linesRemoved"].(int); ok {
					removed = val
				}

				stats["netChange"] = added - removed
			}
		}

		// Format statistics and get basic summary
		statsSummary := formatStatsForDisplay(stats)

		// Get list of commits
		commitList := history.FormatCommitList(commits)

		var aiInsight string
		if useAI {
			aiInsight, err = generateAIInsights(commits, stats, personalityName, cfg)
			if err != nil {
				fmt.Println(color.YellowString("Note:"), "Unable to generate AI insights:", err)
			}
		}

		// Generate the complete summary
		summary := formatSummary(statsSummary, commitList, aiInsight, daysFlag, showCommitHistoryFlag)

		// Export if requested, otherwise print to console
		if exportFlag != "" {
			if err := exportSummary(summary, exportFlag); err != nil {
				fmt.Println(color.RedString("Error:"), "Failed to export summary:", err)
			} else {
				fmt.Println(color.GreenString("Summary exported successfully."))
			}
		} else {
			// Print to console
			fmt.Println(summary)
		}
	},
}

// generateAIInsights creates AI-powered insights for the commit history
func generateAIInsights(commits []history.CommitInfo, stats map[string]interface{}, personalityName string, cfg config.Config) (string, error) {
	// Check if we have any commits to analyze
	if len(commits) == 0 {
		// If no commits found, return a simple message
		return "No commits found in the specified time period to analyze.", nil
	}

	// Build a condensed representation of commit messages
	var commitMessages []string
	for _, commit := range commits {
		commitMessages = append(commitMessages, commit.Message)
	}

	// Create summary context
	summaryContext := feedback.CommitContext{
		Message:       "Weekly Summary Analysis",
		Timestamp:     time.Now(),
		CommitHistory: commitMessages,
		CommitStats:   stats,
	}

	// Load personality configuration to modify
	personalities, err := personality.LoadPersonalities(cfg.Moai.PersonalityFile)
	if err != nil {
		// Fall back to default personalities if there's an error
		personalities = personality.DefaultPersonalities()
	}

	// Get the selected personality
	selectedPersonality, err := personalities.GetPersonality(personalityName)
	if err != nil {
		// Fall back to default personality
		selectedPersonality, _ = personalities.GetPersonality("")
	}

	// Get terminal width for formatting constraints
	width := 80
	if w, _, err := term.GetSize(int(os.Stdout.Fd())); err == nil && w > 0 {
		width = w
	}
	// Account for box borders (typically 4 chars)
	maxLineWidth := width - 8

	// Create a custom personality configuration for summary insights
	customPersonality := selectedPersonality

	// Increase token limit but not excessively
	customPersonality.MaxTokens = 400

	// Create a tailored system prompt for terminal-friendly output
	customPersonality.SystemPrompt = fmt.Sprintf(`You are a Git expert named Moai providing concise, actionable insights about commit history.
Your output MUST fit in a terminal box with maximum line width of %d characters.
Format your response as:

- 2-3 bullet points about commit message patterns
- 1-2 bullet points about work habits/timing
- 2 specific, actionable recommendations

Use plain text formatting suitable for terminals - NO markdown headings or syntax.
Keep each bullet point to 1-2 sentences maximum.
Start each bullet with "• " and skip the introduction - go straight to insights.
Maintain the personality tone (%s) but be extremely concise.`,
		maxLineWidth,
		personalityName,
	)

	// Use a simplified user prompt that focuses on terminal output
	customPersonality.UserPromptFormat = fmt.Sprintf(`Analyze these %d Git commits:
{{range .CommitHistory}}- {{.}}
{{end}}

Stats: {{index .CommitStats "totalCommits"}} commits, {{index .CommitStats "uniqueAuthors"}} authors, 
{{index .CommitStats "filesChanged"}} files changed, +{{index .CommitStats "linesAdded"}} -{{index .CommitStats "linesRemoved"}} lines

Provide CONCISE terminal-friendly insights focusing on patterns, quality, and actionable advice:`,
		len(commitMessages),
	)

	// Create feedback engine with the custom personality
	engine := feedback.NewFeedbackEngineWithCustomPersonality(
		cfg.LLM.Provider,
		cfg.LLM.Model,
		cfg.LLM.APIKey,
		customPersonality,
		false, // Default no debug for summary
	)

	// Generate AI insights
	return engine.GenerateSummaryFeedback(summaryContext)
}

// formatSummary combines all parts into a complete summary
func formatSummary(stats, commits, aiInsights string, days int, showHistory bool) string {
	var result strings.Builder

	// Get terminal width for better formatting
	width := 80
	if w, _, err := term.GetSize(int(os.Stdout.Fd())); err == nil && w > 0 {
		width = w
	}

	// Create styled boxes
	boxStylePrimary := lipgloss.NewStyle().
		BorderStyle(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#2980b9")).
		Padding(0, 1).
		Width(width - 4)

	boxStyleSecondary := lipgloss.NewStyle().
		BorderStyle(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#27ae60")).
		Padding(0, 1).
		Width(width - 4)

	subHeaderStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#2980b9")).
		Bold(true)

	// Statistics section with combined date range and header
	var statsHeader string
	if days >= 365*10 || days == 0 {
		statsHeader = subHeaderStyle.Render("Git Statistics: Complete repository history")
	} else {
		statsHeader = subHeaderStyle.Render(fmt.Sprintf("Git Statistics: Last %d days (%s to %s)",
			days,
			time.Now().AddDate(0, 0, -days).Format("2006-01-02"),
			time.Now().Format("2006-01-02")))
	}
	result.WriteString(statsHeader + "\n")
	result.WriteString(boxStylePrimary.Render(stats))
	result.WriteString("\n\n")

	// AI Insights (if available)
	if aiInsights != "" {
		insightsHeader := subHeaderStyle.Render("AI Insights")
		result.WriteString(insightsHeader + "\n")
		result.WriteString(boxStyleSecondary.Render(aiInsights))
		result.WriteString("\n\n")
	}

	// Only include commit history if explicitly requested
	if showHistory {
		historyHeader := subHeaderStyle.Render("Commit History")
		result.WriteString(historyHeader + "\n")
		result.WriteString(boxStylePrimary.Render(commits))
	}

	return result.String()
}

// formatStatsForDisplay converts the statistics map into a formatted string for console output
func formatStatsForDisplay(stats map[string]interface{}) string {
	var result strings.Builder

	// Terminal width detection
	width := 80
	if w, _, err := term.GetSize(0); err == nil && w > 0 {
		width = w
	}

	// Header
	fmt.Fprintf(&result, "\n%s\n", color.New(color.Bold).Sprintf("📊 Git Repository Statistics"))
	fmt.Fprintf(&result, "%s\n\n", strings.Repeat("─", width/2))

	// Basic statistics
	fmt.Fprintf(&result, "  %s %s\n",
		color.New(color.Bold).Sprintf("Total Commits:"),
		color.CyanString("%v", stats["totalCommits"]))

	fmt.Fprintf(&result, "  %s %s\n",
		color.New(color.Bold).Sprintf("Unique Authors:"),
		color.CyanString("%v", stats["uniqueAuthors"]))

	// Average commits
	if avg, ok := stats["averageCommitsPerDay"].(float64); ok {
		fmt.Fprintf(&result, "  %s %s\n",
			color.New(color.Bold).Sprintf("Average Commits Per Day:"),
			color.CyanString("%.2f", avg))
	}

	// Activity patterns
	if commitsByDay, ok := stats["commitsByDay"].(map[string]int); ok && len(commitsByDay) > 0 {
		fmt.Fprintf(&result, "\n  %s\n", color.New(color.Bold).Sprintf("Activity by Day of Week:"))

		// Find the maximum commits for scaling
		maxCommits := 0
		for _, count := range commitsByDay {
			if count > maxCommits {
				maxCommits = count
			}
		}

		// Display commits by day with bar charts
		days := []string{"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
		for _, day := range days {
			count := commitsByDay[day]
			if count > 0 {
				// Calculate bar length based on percentage of max
				barLength := (count * 20) / maxCommits
				if barLength < 1 {
					barLength = 1
				}

				bar := color.HiBlueString(strings.Repeat("█", barLength))
				fmt.Fprintf(&result, "    %s %s %s (%d)\n",
					color.New(color.Bold).Sprintf("%-9s:", day),
					bar,
					color.HiBlackString(""),
					count)
			}
		}
	}

	// Time activity
	if commitsByHour, ok := stats["commitsByHourRange"].(map[string]int); ok && len(commitsByHour) > 0 {
		fmt.Fprintf(&result, "\n  %s\n", color.New(color.Bold).Sprintf("Activity by Time of Day:"))

		// Find the maximum commits for scaling
		maxCommits := 0
		for _, count := range commitsByHour {
			if count > maxCommits {
				maxCommits = count
			}
		}

		// Define the time ranges in order
		timeRanges := []string{
			"Early Morning (4-8)",
			"Morning (8-12)",
			"Afternoon (12-16)",
			"Evening (16-20)",
			"Night (20-24)",
			"Late Night (0-4)",
		}

		for _, timeRange := range timeRanges {
			if count, ok := commitsByHour[timeRange]; ok && count > 0 {
				// Calculate bar length based on percentage of max
				barLength := (count * 20) / maxCommits
				if barLength < 1 {
					barLength = 1
				}

				bar := color.HiGreenString(strings.Repeat("█", barLength))
				fmt.Fprintf(&result, "    %s %s %s (%d)\n",
					color.New(color.Bold).Sprintf("%-20s:", timeRange),
					bar,
					color.HiBlackString(""),
					count)
			}
		}
	}

	// File statistics
	if fileStats, ok := stats["fileChanges"].(map[string]int); ok && len(fileStats) > 0 {
		total := fileStats["added"] + fileStats["modified"] + fileStats["deleted"]
		if total > 0 {
			fmt.Fprintf(&result, "\n  %s\n", color.New(color.Bold).Sprintf("File Changes:"))
			fmt.Fprintf(&result, "    %s %s\n",
				color.New(color.Bold).Sprintf("Added:"),
				color.GreenString("%d", fileStats["added"]))
			fmt.Fprintf(&result, "    %s %s\n",
				color.New(color.Bold).Sprintf("Modified:"),
				color.YellowString("%d", fileStats["modified"]))
			fmt.Fprintf(&result, "    %s %s\n",
				color.New(color.Bold).Sprintf("Deleted:"),
				color.RedString("%d", fileStats["deleted"]))
		}
	}

	// Line changes
	if lineChanges, ok := stats["linesChanged"].(map[string]int); ok {
		additions := lineChanges["additions"]
		deletions := lineChanges["deletions"]
		if additions > 0 || deletions > 0 {
			fmt.Fprintf(&result, "\n  %s\n", color.New(color.Bold).Sprintf("Line Changes:"))
			fmt.Fprintf(&result, "    %s %s\n",
				color.New(color.Bold).Sprintf("Additions:"),
				color.GreenString("+%d", additions))
			fmt.Fprintf(&result, "    %s %s\n",
				color.New(color.Bold).Sprintf("Deletions:"),
				color.RedString("-%d", deletions))

			// Net change
			net := additions - deletions
			netColor := color.GreenString
			if net < 0 {
				netColor = color.RedString
			}
			fmt.Fprintf(&result, "    %s %s\n",
				color.New(color.Bold).Sprintf("Net Change:"),
				netColor("%+d", net))
		}
	}

	return result.String()
}

// exportSummary exports the summary to a file in the requested format
func exportSummary(summary, format string) error {
	// Determine output filename
	timestamp := time.Now().Format("2006-01-02")
	var filename string

	// Convert ANSI color codes to appropriate format
	plainSummary := stripANSIColors(summary)

	switch strings.ToLower(format) {
	case "text", "txt":
		filename = fmt.Sprintf("git-summary-%s.txt", timestamp)
		return os.WriteFile(filename, []byte(plainSummary), 0644)

	case "markdown", "md":
		filename = fmt.Sprintf("git-summary-%s.md", timestamp)
		return os.WriteFile(filename, []byte(convertToMarkdown(plainSummary)), 0644)

	case "html":
		filename = fmt.Sprintf("git-summary-%s.html", timestamp)
		return os.WriteFile(filename, []byte(convertToHTML(plainSummary)), 0644)

	default:
		return fmt.Errorf("unsupported export format: %s", format)
	}
}

// stripANSIColors removes ANSI color codes from a string
func stripANSIColors(s string) string {
	// Simple regex to remove ANSI color codes
	return color.New().SprintFunc()(s)
}

// convertToMarkdown converts the summary to Markdown format
func convertToMarkdown(summary string) string {
	lines := strings.Split(summary, "\n")
	var result strings.Builder

	for _, line := range lines {
		if strings.HasPrefix(line, "##") {
			// Convert "## Title" to "## Title"
			result.WriteString(line + "\n")
		} else if strings.HasPrefix(line, "📊 Git Activity Summary") {
			result.WriteString("# " + strings.TrimPrefix(line, "📊 ") + "\n")
		} else if strings.Contains(line, "Last") && strings.Contains(line, "days") {
			result.WriteString("*" + line + "*\n\n")
		} else {
			result.WriteString(line + "\n")
		}
	}

	return result.String()
}

// convertToHTML converts the summary to HTML format
func convertToHTML(summary string) string {
	markdown := convertToMarkdown(summary)

	// Simple HTML wrapper
	html := `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git Activity Summary</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1 { color: #2c3e50; }
        h2 { color: #2980b9; }
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .commit-list {
            list-style-type: none;
            padding-left: 0;
        }
        .commit-item {
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        .stats {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-box {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            flex: 1 1 200px;
        }
    </style>
</head>
<body>
    <div class="content">
        %s
    </div>
</body>
</html>
`

	// Replace Markdown with HTML tags
	htmlContent := strings.ReplaceAll(markdown, "# ", "<h1>")
	htmlContent = strings.ReplaceAll(htmlContent, "\n## ", "</h1>\n<h2>")
	htmlContent = strings.ReplaceAll(htmlContent, "\n", "<br>")
	htmlContent = strings.ReplaceAll(htmlContent, "</h1>", "</h1>")
	htmlContent = strings.ReplaceAll(htmlContent, "</h2>", "</h2>")

	return fmt.Sprintf(html, htmlContent)
}
