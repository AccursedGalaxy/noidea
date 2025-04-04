package cmd

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/AccursedGalaxy/noidea/internal/github"
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
)

func init() {
	rootCmd.AddCommand(issueCmd)
	
	// Add subcommands
	issueCmd.AddCommand(issueListCmd)
	issueCmd.AddCommand(issueViewCmd)
	issueCmd.AddCommand(issueCreateCmd)

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
		
		// Check if we have a token
		_, err = auth.GetToken()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub token not found. Please configure it with 'noidea config github-auth'")
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
			color.CyanString("Issues"), 
			color.YellowString(repo.Owner), 
			color.YellowString(repo.Name))
		
		for _, issue := range issues {
			// Format issue number and title
			prefix := fmt.Sprintf("#%-4d", issue.Number)
			
			// Colorize state
			stateColor := color.New(color.FgGreen)
			if issue.State == "closed" {
				stateColor = color.New(color.FgRed)
			}
			
			// Format date
			timeAgo := formatTimeAgo(issue.UpdatedAt)
			
			// Format labels
			labelStr := ""
			if len(issue.Labels) > 0 {
				labelStr = " [" + strings.Join(issue.Labels, ", ") + "]"
			}
			
			// Print summary
			fmt.Printf("%s %s %s%s %s\n",
				color.YellowString(prefix),
				stateColor.Sprint(issue.State),
				issue.Title,
				color.CyanString(labelStr),
				color.WhiteString("(updated %s)", timeAgo))
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
		
		// Check if we have a token
		_, err = auth.GetToken()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub token not found. Please configure it with 'noidea config github-auth'")
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
		fmt.Println(color.CyanString("\nDescription:"))
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
		
		// Check if we have a token
		_, err = auth.GetToken()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub token not found. Please configure it with 'noidea config github-auth'")
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
	
	// TODO: Replace with actual AI implementation
	// For now, we'll use a simple prompt
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
	// In a real implementation, this would call the LLM service

	// For now, just use a simple template
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