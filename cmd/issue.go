package cmd

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/AccursedGalaxy/noidea/internal/config"
	"github.com/AccursedGalaxy/noidea/internal/feedback"
	"github.com/AccursedGalaxy/noidea/internal/github"
	"github.com/AccursedGalaxy/noidea/internal/personality"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

var (
	// Issue flags
	issueStateFlag       string
	issueLimitFlag       int
	issueLabelsFlag      []string
	issueBodyFlag        string
	issueWithAIFlag      bool
	issueOnlyOpenFlag    bool
	issueOnlyClosedFlag  bool
	issueTitleFlag       string
	issuePersonalityFlag string
)

func init() {
	rootCmd.AddCommand(issueCmd)
	
	// Add subcommands
	issueCmd.AddCommand(issueListCmd)
	issueCmd.AddCommand(issueViewCmd)
	issueCmd.AddCommand(issueCreateCmd)
	issueCmd.AddCommand(issueCloseCmd)

	// Add flags to issue list command
	issueListCmd.Flags().StringVarP(&issueStateFlag, "state", "s", "open", "Filter issues by state (open, closed, all)")
	issueListCmd.Flags().IntVarP(&issueLimitFlag, "limit", "l", 10, "Maximum number of issues to display")
	issueListCmd.Flags().BoolVarP(&issueOnlyOpenFlag, "open", "o", false, "Show only open issues")
	issueListCmd.Flags().BoolVarP(&issueOnlyClosedFlag, "closed", "c", false, "Show only closed issues")
	
	// Add flags to issue create command
	issueCreateCmd.Flags().StringVarP(&issueTitleFlag, "title", "t", "", "Issue title")
	issueCreateCmd.Flags().StringVarP(&issueBodyFlag, "body", "b", "", "Issue body")
	issueCreateCmd.Flags().StringSliceVarP(&issueLabelsFlag, "labels", "l", []string{}, "Labels to apply to the issue")
	issueCreateCmd.Flags().BoolVarP(&issueWithAIFlag, "ai", "a", false, "Use AI to help create the issue")
	issueCreateCmd.Flags().StringVarP(&issuePersonalityFlag, "personality", "p", "", "Personality to use for AI issue creation")

	// Add flags to issue close command
	issueCloseCmd.Flags().BoolP("quiet", "q", false, "Suppress output (for use in scripts)")
	issueCloseCmd.Flags().StringP("comment", "c", "", "Add a closing comment")
}

var issueCmd = &cobra.Command{
	Use:   "issue",
	Short: "Manage GitHub issues",
	Long:  `View, create, and manage GitHub issues for the current repository.`,
	Run: func(cmd *cobra.Command, args []string) {
		// If no subcommand is provided, display help
		cmd.Help()
	},
}

var issueListCmd = &cobra.Command{
	Use:   "list",
	Short: "List GitHub issues",
	Long:  `List GitHub issues for the current repository.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Override state flag based on --open or --closed flags
		if issueOnlyOpenFlag {
			issueStateFlag = "open"
		} else if issueOnlyClosedFlag {
			issueStateFlag = "closed"
		}
		
		// Get current repository
		repo, err := github.GetCurrentRepo()
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		// Create GitHub authenticator
		auth := github.NewAuthenticator()
		
		// Check authentication - we need API access for issue operations
		_, err = auth.Client()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub authentication not configured. Please configure it with 'noidea config github-auth'")
			return
		}
		
		// Create issue service and list issues
		issueService := github.NewIssueService(auth)
		issues, err := issueService.ListIssues(repo.Owner, repo.Name, issueStateFlag, issueLimitFlag)
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		// Display issues
		if len(issues) == 0 {
			fmt.Println(color.YellowString("No issues found"))
			return
		}
		
		fmt.Printf("%s for %s/%s:\n\n",
			color.CyanString("Issues (%s)", issueStateFlag),
			color.YellowString(repo.Owner),
			color.YellowString(repo.Name))
		
		// Calculate column widths for consistent formatting
		maxNumWidth := len(fmt.Sprintf("%d", issues[0].Number))
		for _, issue := range issues {
			width := len(fmt.Sprintf("%d", issue.Number))
			if width > maxNumWidth {
				maxNumWidth = width
			}
		}
		
		for _, issue := range issues {
			// Format state
			stateColor := color.New(color.FgGreen)
			if issue.State == "closed" {
				stateColor = color.New(color.FgRed)
			}
			
			// Format date
			var timeAgo string
			if time.Since(issue.UpdatedAt) < 24*time.Hour {
				timeAgo = fmt.Sprintf("%s ago", formatDuration(time.Since(issue.UpdatedAt)))
			} else {
				timeAgo = issue.UpdatedAt.Format("Jan 2")
			}
			
			// Display issue
			fmt.Printf("#%-*d %s %s %s\n",
				maxNumWidth,
				issue.Number,
				truncateString(issue.Title, 60),
				stateColor.Sprint(issue.State),
				color.New(color.FgBlue).Sprint(timeAgo))
		}
	},
}

var issueViewCmd = &cobra.Command{
	Use:   "view [issue number]",
	Short: "View a GitHub issue",
	Long:  `View details of a specific GitHub issue.`,
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		// Parse issue number
		issueNumber, err := strconv.Atoi(args[0])
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Invalid issue number")
			return
		}
		
		// Get current repository
		repo, err := github.GetCurrentRepo()
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		// Create GitHub authenticator
		auth := github.NewAuthenticator()
		
		// Check authentication - we need API access for issue operations
		_, err = auth.Client()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub authentication not configured. Please configure it with 'noidea config github-auth'")
			return
		}
		
		// Create issue service and get issue
		issueService := github.NewIssueService(auth)
		issue, err := issueService.GetIssue(repo.Owner, repo.Name, issueNumber)
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		// Format issue state
		stateColor := color.New(color.FgGreen)
		if issue.State == "closed" {
			stateColor = color.New(color.FgRed)
		}
		
		// Display issue
		fmt.Println(color.CyanString("Issue #%d: %s", issue.Number, issue.Title))
		fmt.Printf("State: %s\n", stateColor.Sprint(issue.State))
		fmt.Printf("Author: %s\n", issue.Author)
		fmt.Printf("Created: %s\n", issue.CreatedAt.Format("2006-01-02 15:04:05"))
		fmt.Printf("Updated: %s\n", issue.UpdatedAt.Format("2006-01-02 15:04:05"))
		
		// Display labels if any
		if len(issue.Labels) > 0 {
			fmt.Printf("Labels: %s\n", strings.Join(issue.Labels, ", "))
		}
		
		// Display assignees if any
		if len(issue.Assignees) > 0 {
			fmt.Printf("Assignees: %s\n", strings.Join(issue.Assignees, ", "))
		}
		
		// Display milestone if any
		if issue.Milestone != "" {
			fmt.Printf("Milestone: %s\n", issue.Milestone)
		}
		
		// Display body
		fmt.Println(issue.Body)
		
		// Display URL
		fmt.Println(color.CyanString("\nURL:"), issue.URL)
	},
}

var issueCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a GitHub issue",
	Long:  `Create a new GitHub issue in the current repository.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Get current repository
		repo, err := github.GetCurrentRepo()
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		// Create GitHub authenticator
		auth := github.NewAuthenticator()
		
		// Check authentication - we need API access for issue operations
		_, err = auth.Client()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub authentication not configured. Please configure it with 'noidea config github-auth'")
			return
		}
		
		// If AI flag is set, help create the issue
		if issueWithAIFlag {
			createIssueWithAI(repo)
			return
		}
		
		// Interactive mode if title not provided
		if issueTitleFlag == "" {
			reader := bufio.NewReader(os.Stdin)
			
			fmt.Print("Issue title: ")
			title, _ := reader.ReadString('\n')
			issueTitleFlag = strings.TrimSpace(title)
			
			if issueTitleFlag == "" {
				fmt.Println(color.RedString("Error:"), "Issue title is required")
				return
			}
			
			fmt.Println("Issue body (end with an empty line):")
			var bodyBuilder strings.Builder
			for {
				line, _ := reader.ReadString('\n')
				line = strings.TrimRight(line, "\r\n")
				if line == "" {
					break
				}
				bodyBuilder.WriteString(line)
				bodyBuilder.WriteString("\n")
			}
			issueBodyFlag = bodyBuilder.String()
			
			fmt.Print("Labels (comma-separated): ")
			labelsStr, _ := reader.ReadString('\n')
			labelsStr = strings.TrimSpace(labelsStr)
			if labelsStr != "" {
				issueLabelsFlag = strings.Split(labelsStr, ",")
				for i := range issueLabelsFlag {
					issueLabelsFlag[i] = strings.TrimSpace(issueLabelsFlag[i])
				}
			}
		}
		
		// Create issue service and create issue
		issueService := github.NewIssueService(auth)
		issue, err := issueService.CreateIssue(
			repo.Owner, 
			repo.Name, 
			issueTitleFlag, 
			issueBodyFlag, 
			issueLabelsFlag,
		)
		
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		fmt.Println(color.GreenString("Issue #%d created successfully:", issue.Number), issue.Title)
		fmt.Println(color.CyanString("URL:"), issue.URL)
	},
}

var issueCloseCmd = &cobra.Command{
	Use:   "close [issue number]",
	Short: "Close a GitHub issue",
	Long:  `Close a specific GitHub issue.`,
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		// Parse issue number
		issueNumber, err := strconv.Atoi(args[0])
		if err != nil {
			fmt.Println(color.RedString("Error:"), "Invalid issue number")
			return
		}
		
		// Get current repository
		repo, err := github.GetCurrentRepo()
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		// Create GitHub authenticator
		auth := github.NewAuthenticator()
		
		// Check authentication - we need API access for issue operations
		_, err = auth.Client()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub authentication not configured. Please configure it with 'noidea config github-auth'")
			return
		}
		
		// Create issue service and close issue
		issueService := github.NewIssueService(auth)
		quiet, _ := cmd.Flags().GetBool("quiet")
		comment, _ := cmd.Flags().GetString("comment")
		
		// Add comment if provided
		if comment != "" && !quiet {
			fmt.Println(color.CyanString("Adding closing comment..."))
		}
		
		err = issueService.CloseIssue(repo.Owner, repo.Name, issueNumber, comment)
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		if !quiet {
			fmt.Println(color.GreenString("Issue #%d closed successfully", issueNumber))
		}
	},
}

// createIssueWithAI helps create an issue using AI
func createIssueWithAI(repo *github.RepoInfo) {
	fmt.Println(color.CyanString("Creating issue with AI assistance"))
	
	// Ask for issue description
	reader := bufio.NewReader(os.Stdin)
	fmt.Println("Describe the issue or feature you want to create:")
	var descBuilder strings.Builder
	for {
		line, _ := reader.ReadString('\n')
		line = strings.TrimRight(line, "\r\n")
		if line == "" {
			break
		}
		descBuilder.WriteString(line)
		descBuilder.WriteString("\n")
	}
	userDescription := strings.TrimSpace(descBuilder.String())
	
	if userDescription == "" {
		fmt.Println(color.RedString("Error:"), "Issue description is required")
		return
	}
	
	// Use AI to generate a well-formed issue
	fmt.Println(color.CyanString("Generating issue..."))
	
	// Generate issue using our existing AI system
	aiTitle, aiBody := generateIssueWithAI(userDescription, repo)
	
	// Display generated issue
	fmt.Println(color.CyanString("\nGenerated Issue:"))
	fmt.Println(color.YellowString("Title:"), aiTitle)
	fmt.Println(color.YellowString("Body:"))
	fmt.Println(aiBody)
	
	// Ask for confirmation
	fmt.Print(color.CyanString("\nCreate this issue? [Y/n]: "))
	confirm, _ := reader.ReadString('\n')
	confirm = strings.TrimSpace(strings.ToLower(confirm))
	
	if confirm == "n" || confirm == "no" {
		fmt.Println(color.YellowString("Issue creation cancelled"))
		return
	}
	
	// Create GitHub authenticator
	auth := github.NewAuthenticator()
	
	// Check token authentication
	_, err := auth.GetToken()
	if err != nil {
		fmt.Println(color.RedString("Error:"), "GitHub authentication not configured. Please configure it with 'noidea config github-auth'")
		return
	}
	
	// Create issue service and create issue
	issueService := github.NewIssueService(auth)
	issue, err := issueService.CreateIssue(
		repo.Owner,
		repo.Name,
		aiTitle,
		aiBody,
		issueLabelsFlag,
	)
	
	if err != nil {
		fmt.Println(color.RedString("Error:"), err)
		return
	}
	
	fmt.Println(color.GreenString("Issue #%d created successfully:", issue.Number), issue.Title)
	fmt.Println(color.CyanString("URL:"), issue.URL)
}

// generateIssueWithAI creates a well-formed issue from a user description
func generateIssueWithAI(description string, repo *github.RepoInfo) (string, string) {
	// Load configuration
	cfg := config.LoadConfig()
	
	// Check if LLM is enabled
	if !cfg.LLM.Enabled {
		// Fallback to template if AI is not enabled
		return generateSimpleIssueTemplate(description, repo)
	}
	
	// Get personality name from flag or default
	personalityName := cfg.Moai.Personality
	if issuePersonalityFlag != "" {
		personalityName = issuePersonalityFlag
	}
	
	// Create feedback engine using existing system
	// Note: We're intentionally not using the default engine here since we need specific formatting
	_ = feedback.NewFeedbackEngine(
		cfg.LLM.Provider,
		cfg.LLM.Model,
		cfg.LLM.APIKey,
		personalityName,
		cfg.Moai.PersonalityFile,
	)
	
	// Define custom personality for issue creation if needed
	issuePersonality := personality.Personality{
		Name:             "issue_creator",
		Description:      "GitHub Issue Creator",
		SystemPrompt:     "You are a helpful assistant that creates well-structured GitHub issues from user descriptions. Format the issue in a clear, professional way with appropriate sections like Description, Expected Behavior, Steps to Reproduce, etc.",
		UserPromptFormat: "Create a GitHub issue for the following description:\n\n{{.Message}}\n\nFor repository: {{.Username}}/{{.RepoName}}\n\nProvide both a concise title and a detailed body with proper Markdown formatting. Separate the title and body with '---' on its own line.",
		MaxTokens:        800,
		Temperature:      0.7,
	}
	
	// Create a specialized engine with the issue personality
	issueEngine := feedback.NewFeedbackEngineWithCustomPersonality(
		cfg.LLM.Provider,
		cfg.LLM.Model,
		cfg.LLM.APIKey,
		issuePersonality,
	)
	
	// Create commit context with the description
	ctx := feedback.CommitContext{
		Message:   description,
		Timestamp: time.Now(),
	}
	
	// Try to get repo details to provide context
	ctx.CommitHistory = []string{} // Empty array for no history
	
	// Generate AI response
	aiResponse, err := issueEngine.GenerateFeedback(ctx)
	if err != nil {
		fmt.Println(color.YellowString("AI generation failed:"), err)
		fmt.Println(color.YellowString("Falling back to template..."))
		return generateSimpleIssueTemplate(description, repo)
	}
	
	// Split response into title and body at the delimiter
	parts := strings.Split(aiResponse, "---")
	if len(parts) < 2 {
		// If response doesn't follow the format, fall back to template
		return generateSimpleIssueTemplate(description, repo)
	}
	
	title := strings.TrimSpace(parts[0])
	body := strings.TrimSpace(parts[1])
	
	// Add reference to noidea CLI
	body += "\n\n---\n_Generated with noidea CLI_"
	
	return title, body
}

// generateSimpleIssueTemplate creates a basic issue template without AI
func generateSimpleIssueTemplate(description string, repo *github.RepoInfo) (string, string) {
	// Create a simple title from the first line
	title := fmt.Sprintf("Issue from description: %s", strings.Split(description, "\n")[0])
	if len(title) > 60 {
		title = title[:57] + "..."
	}
	
	body := fmt.Sprintf(`## Description

%s

## Expected Behavior

[What should happen]

## Current Behavior

[What happens instead]

## Possible Solution

[Ideas for implementing this feature or fixing the issue]

## Steps to Reproduce

1. [Step one]
2. [Step two]
3. [Step three]

## Environment

- Repository: %s/%s
- Generated with noidea CLI`, description, repo.Owner, repo.Name)
	
	return title, body
}

// formatTimeAgo formats a time.Time as a human-readable "time ago" string
func formatTimeAgo(t time.Time) string {
	duration := time.Since(t)
	
	if duration < time.Minute {
		return "just now"
	} else if duration < time.Hour {
		minutes := int(duration.Minutes())
		if minutes == 1 {
			return "1 minute ago"
		}
		return fmt.Sprintf("%d minutes ago", minutes)
	} else if duration < 24*time.Hour {
		hours := int(duration.Hours())
		if hours == 1 {
			return "1 hour ago"
		}
		return fmt.Sprintf("%d hours ago", hours)
	} else if duration < 30*24*time.Hour {
		days := int(duration.Hours() / 24)
		if days == 1 {
			return "1 day ago"
		}
		return fmt.Sprintf("%d days ago", days)
	} else if duration < 365*24*time.Hour {
		months := int(duration.Hours() / 24 / 30)
		if months == 1 {
			return "1 month ago"
		}
		return fmt.Sprintf("%d months ago", months)
	} else {
		years := int(duration.Hours() / 24 / 365)
		if years == 1 {
			return "1 year ago"
		}
		return fmt.Sprintf("%d years ago", years)
	}
}

// formatDuration formats a time.Duration as a human-readable string
func formatDuration(d time.Duration) string {
	if d < time.Minute {
		return fmt.Sprintf("%d seconds", int(d.Seconds()))
	} else if d < time.Hour {
		minutes := int(d.Minutes())
		if minutes == 1 {
			return "1 minute"
		}
		return fmt.Sprintf("%d minutes", minutes)
	} else if d < 24*time.Hour {
		hours := int(d.Hours())
		if hours == 1 {
			return "1 hour"
		}
		return fmt.Sprintf("%d hours", hours)
	} else if d < 30*24*time.Hour {
		days := int(d.Hours() / 24)
		if days == 1 {
			return "1 day"
		}
		return fmt.Sprintf("%d days", days)
	} else if d < 365*24*time.Hour {
		months := int(d.Hours() / 24 / 30)
		if months == 1 {
			return "1 month"
		}
		return fmt.Sprintf("%d months", months)
	} else {
		years := int(d.Hours() / 24 / 365)
		if years == 1 {
			return "1 year"
		}
		return fmt.Sprintf("%d years", years)
	}
}

// truncateString truncates a string to a specified length
func truncateString(s string, maxLength int) string {
	if len(s) > maxLength {
		return s[:maxLength] + "..."
	}
	return s
} 