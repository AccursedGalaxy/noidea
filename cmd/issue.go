package cmd

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
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
	issueFileRefsFlag    []string  // New flag for file references
	issueContextFlag     string    // New flag for providing additional context
	issueCodeScanFlag    bool      // New flag to scan code context in current directory
)

func init() {
	rootCmd.AddCommand(issueCmd)
	
	// Add subcommands
	issueCmd.AddCommand(issueListCmd)
	issueCmd.AddCommand(issueViewCmd)
	issueCmd.AddCommand(issueCreateCmd)
	issueCmd.AddCommand(issueCloseCmd)
	issueCmd.AddCommand(issueCommentCmd) // New command for adding comments

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
	issueCreateCmd.Flags().StringSliceVarP(&issueFileRefsFlag, "files", "f", []string{}, "File paths to include in the issue (only relevant portions will be extracted)")
	issueCreateCmd.Flags().StringVarP(&issueContextFlag, "context", "x", "", "Additional context to provide to AI")
	issueCreateCmd.Flags().BoolVarP(&issueCodeScanFlag, "scan", "s", false, "Scan current directory for relevant code context")

	// Add flags to issue close command
	issueCloseCmd.Flags().BoolP("quiet", "q", false, "Suppress output (for use in scripts)")
	issueCloseCmd.Flags().StringP("comment", "c", "", "Add a closing comment")
	issueCloseCmd.Flags().BoolP("ai", "a", false, "Use AI to generate a closing comment")
	
	// Add flags to issue comment command
	issueCommentCmd.Flags().StringP("body", "b", "", "Comment text")
	issueCommentCmd.Flags().BoolP("ai", "a", false, "Use AI to generate a comment")
	issueCommentCmd.Flags().StringSliceP("files", "f", []string{}, "File paths to include in the comment (only relevant portions will be extracted)")
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
		useAI, _ := cmd.Flags().GetBool("ai")
		
		// Add comment if provided
		if comment != "" && !quiet {
			fmt.Println(color.CyanString("Adding closing comment..."))
		}
		
		// If AI is requested, generate a comment
		if useAI {
			if comment == "" {
				// Interactive mode for AI comment
				reader := bufio.NewReader(os.Stdin)
				fmt.Println("What would you like to comment about? (end with an empty line)")
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
				comment = bodyBuilder.String()
			}
			
			if comment == "" {
				fmt.Println(color.RedString("Error:"), "Comment description is required")
				return
			}
			
			// Generate AI comment
			fmt.Println(color.CyanString("Generating comment..."))
			comment = generateCommentWithAI(comment, issueNumber, repo)
			
			// Display the generated comment
			fmt.Println(color.CyanString("\nGenerated Comment:"))
			fmt.Println(comment)
			
			// Ask for confirmation
			reader := bufio.NewReader(os.Stdin)
			fmt.Print(color.CyanString("\nAdd this comment? [Y/n]: "))
			confirm, _ := reader.ReadString('\n')
			confirm = strings.TrimSpace(strings.ToLower(confirm))
			
			if confirm == "n" || confirm == "no" {
				fmt.Println(color.YellowString("Comment cancelled"))
				return
			}
		}
		
		// Check if we have a comment body
		if comment == "" {
			// Interactive mode for manual comment
			reader := bufio.NewReader(os.Stdin)
			fmt.Println("Enter your comment (end with an empty line):")
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
			comment = bodyBuilder.String()
			
			if comment == "" {
				fmt.Println(color.RedString("Error:"), "Comment body is required")
				return
			}
		}
		
		// Create issue service and close issue
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
	
	// If no body is provided on command line, ask for it
	userDescription := issueBodyFlag
	if userDescription == "" {
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
		userDescription = strings.TrimSpace(descBuilder.String())
	}
	
	if userDescription == "" {
		fmt.Println(color.RedString("Error:"), "Issue description is required")
		return
	}
	
	// Process file references if any are provided
	codeRefs := make(map[string]string)
	if len(issueFileRefsFlag) > 0 {
		fmt.Println(color.CyanString("Processing file references..."))
		for _, filePath := range issueFileRefsFlag {
			content, err := os.ReadFile(filePath)
			if err != nil {
				fmt.Println(color.YellowString("Warning:"), "Could not read file", filePath, ":", err)
				continue
			}
			codeRefs[filePath] = string(content)
			
			// Add reference in description
			if !strings.Contains(userDescription, fmt.Sprintf("{file:%s}", filePath)) {
				userDescription += fmt.Sprintf("\n\nReference to file {file:%s}", filePath)
			}
		}
	}
	
	// Scan for code context if requested
	if issueCodeScanFlag {
		fmt.Println(color.CyanString("Scanning for code context..."))
		// Get the current git status to see what files have been changed
		changedFiles, err := getChangedFiles()
		if err == nil && len(changedFiles) > 0 {
			// Add the first 3 changed files as context
			maxFiles := 3
			if len(changedFiles) < maxFiles {
				maxFiles = len(changedFiles)
			}
			
			for i := 0; i < maxFiles; i++ {
				filePath := changedFiles[i]
				content, err := os.ReadFile(filePath)
				if err != nil {
					continue
				}
				codeRefs[filePath] = string(content)
				userDescription += fmt.Sprintf("\n\nReference to recently changed file {file:%s}", filePath)
			}
		}
	}
	
	// Use AI to generate a well-formed issue
	fmt.Println(color.CyanString("Generating issue..."))
	
	// Generate issue using our existing AI system
	aiTitle, aiBody := generateIssueWithAI(userDescription, repo, codeRefs, issueContextFlag)
	
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
	
	// Create issue service and create issue with code references
	issueService := github.NewIssueService(auth)
	issue, err := issueService.CreateIssueWithCodeRefs(
		repo.Owner,
		repo.Name,
		aiTitle,
		aiBody,
		issueLabelsFlag,
		codeRefs,
	)
	
	if err != nil {
		fmt.Println(color.RedString("Error:"), err)
		return
	}
	
	fmt.Println(color.GreenString("Issue #%d created successfully:", issue.Number), issue.Title)
	fmt.Println(color.CyanString("URL:"), issue.URL)
}

// generateIssueWithAI creates a well-formed issue from a user description
func generateIssueWithAI(description string, repo *github.RepoInfo, codeRefs map[string]string, additionalContext string) (string, string) {
	// Load configuration
	cfg := config.LoadConfig()
	
	// Check if LLM is enabled
	if !cfg.LLM.Enabled {
		// Fallback to template if AI is not enabled
		return generateSimpleIssueTemplate(description, repo)
	}
	
	// Build an enhanced system prompt that includes code context awareness
	systemPrompt := `You are a technical project manager and expert developer creating detailed GitHub issues.
Your task is to analyze the user's description and any code references to create a comprehensive, actionable issue.

For each issue, you must:
1. Create a descriptive title that summarizes the main point
2. Write a detailed description section that explains the issue or feature
3. Fill in the "Expected Behavior" section with clear, concrete objectives and technical details
4. Fill in the "Current Behavior" section with specific details about the current implementation or limitations
5. Suggest concrete implementation approaches in the "Possible Solution" section, including code patterns, architectures, or technologies to use
6. Include specific, actionable "Steps to Reproduce" for bugs, or implementation steps for features
7. Format the issue using proper Markdown

IMPORTANT: 
- Do NOT use placeholder text like "[What should happen]" or "[Step one]"
- You MUST provide ACTUAL technical details in every section
- Your response should be immediately usable as a thorough development ticket
- If implementing a feature, describe how it should be implemented technically
- If fixing a bug, describe both the current behavior and what needs to be fixed

When code references are provided:
- Analyze the code structure and purpose
- Reference specific functions, classes, or patterns in your solution
- Suggest specific code changes or approaches based on the existing architecture
- Consider dependencies and potential impact on other parts of the codebase

Your issues should be technically precise, actionable, and provide clear direction for developers.`

	// Build an enhanced user prompt that includes code context
	userPromptFormat := "Create a detailed GitHub issue for the following description:\n\n{{.Message}}\n\n"
	
	// Add code references if available
	if len(codeRefs) > 0 {
		userPromptFormat += "Referenced code files (analyze these to provide specific implementation details):\n\n"
		for filePath, content := range codeRefs {
			// Limit file content to avoid token limits
			contentPreview := content
			if len(contentPreview) > 2000 {
				contentPreview = contentPreview[:2000] + "...[truncated]"
			}
			userPromptFormat += fmt.Sprintf("File: %s\n```\n%s\n```\n\n", filePath, contentPreview)
		}
	}
	
	// Add additional context if provided
	if additionalContext != "" {
		userPromptFormat += fmt.Sprintf("Additional context:\n%s\n\n", additionalContext)
	}
	
	// Add repo info for more context
	userPromptFormat += "Repository information:\n"
	userPromptFormat += fmt.Sprintf("- Owner/Name: {{.Username}}/{{.RepoName}}\n")
	
	// Add instructions for response format
	userPromptFormat += "\nFormat your response with the following sections, filling them with specific details based on your analysis:\n"
	userPromptFormat += "1. First line: A concise, descriptive title\n"
	userPromptFormat += "2. \"---\" separator on its own line\n"
	userPromptFormat += "3. ## Description - A comprehensive explanation of the issue or feature\n"
	userPromptFormat += "4. ## Expected Behavior - CONCRETE description of what should happen when implemented (do not use placeholders)\n"
	userPromptFormat += "5. ## Current Behavior - CONCRETE description of the current state (do not use placeholders)\n"
	userPromptFormat += "6. ## Possible Solution - DETAILED implementation suggestions with specific approach (do not use placeholders)\n"
	userPromptFormat += "7. ## Steps to Reproduce/Implement - SPECIFIC, actionable steps (do not use placeholders)\n"
	userPromptFormat += "\nIMPORTANT: Do NOT use placeholder text like '[What should happen]'. You MUST include actual technical details, implementation ideas, and specific steps in each section.\n"
	
	// Define custom personality for issue creation
	issuePersonality := personality.Personality{
		Name:             "issue_creator",
		Description:      "GitHub Issue Creator",
		SystemPrompt:     systemPrompt,
		UserPromptFormat: userPromptFormat,
		MaxTokens:        2500, // Increased token limit to handle code references and detailed analysis
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
	
	// Add code context as diff if available
	if len(codeRefs) > 0 {
		var diffBuilder strings.Builder
		for filePath, content := range codeRefs {
			diffBuilder.WriteString(fmt.Sprintf("diff --git a/%s b/%s\n", filePath, filePath))
			diffBuilder.WriteString(fmt.Sprintf("--- a/%s\n", filePath))
			diffBuilder.WriteString(fmt.Sprintf("+++ b/%s\n", filePath))
			// Add a simple diff marker
			diffBuilder.WriteString("@@ -0,0 +1 @@\n")
			// Add some content as context (limiting to avoid token issues)
			contentLines := strings.Split(content, "\n")
			maxLines := 150 // Increased for better context
			if len(contentLines) > maxLines {
				contentLines = contentLines[:maxLines]
				contentLines = append(contentLines, "... (truncated)")
			}
			for _, line := range contentLines {
				diffBuilder.WriteString("+" + line + "\n")
			}
			diffBuilder.WriteString("\n")
		}
		ctx.Diff = diffBuilder.String()
	}
	
	// Get commit history for additional context
	ctx.CommitHistory = []string{} // Empty array for no history
	
	// Collect additional repository context to help the AI
	repoContext := ""
	
	// Check for commonly important files for context
	commonFiles := []string{"README.md", "CONTRIBUTING.md", "ROADMAP.md", "TODO.md"}
	for _, filename := range commonFiles {
		if _, err := os.Stat(filename); err == nil {
			data, err := os.ReadFile(filename)
			if err == nil && len(data) > 0 {
				// Limit the amount of context to avoid token overflow
				preview := string(data)
				if len(preview) > 1000 {
					preview = preview[:1000] + "...[truncated]"
				}
				repoContext += fmt.Sprintf("Contents of %s:\n```\n%s\n```\n\n", filename, preview)
			}
		}
	}
	
	// Add this context if we found any
	if repoContext != "" {
		ctx.Message += "\n\nRepository Context:\n" + repoContext
	}
	
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
	
	// Process file references - replace placeholder markers with actual references
	// Note: The actual file content will be inserted when creating the issue
	for filePath := range codeRefs {
		marker := fmt.Sprintf("File: %s", filePath)
		if strings.Contains(body, marker) {
			body = strings.Replace(body, marker+"\n```", fmt.Sprintf("File: {file:%s}\n```", filePath), -1)
		}
	}
	
	// Add reference to noidea CLI
	body += "\n\n## Environment\n\n- Repository: " + repo.Owner + "/" + repo.Name + "\n- Generated with noidea CLI"
	
	return title, body
}

// getChangedFiles returns a list of files that have been changed in the current git repository
func getChangedFiles() ([]string, error) {
	cmd := exec.Command("git", "diff", "--name-only", "HEAD")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}
	
	files := strings.Split(strings.TrimSpace(string(output)), "\n")
	
	// Check for staged files
	cmd = exec.Command("git", "diff", "--name-only", "--staged")
	stagedOutput, err := cmd.Output()
	if err == nil && len(stagedOutput) > 0 {
		stagedFiles := strings.Split(strings.TrimSpace(string(stagedOutput)), "\n")
		files = append(files, stagedFiles...)
	}
	
	// Check for untracked files
	cmd = exec.Command("git", "ls-files", "--others", "--exclude-standard")
	untrackedOutput, err := cmd.Output()
	if err == nil && len(untrackedOutput) > 0 {
		untrackedFiles := strings.Split(strings.TrimSpace(string(untrackedOutput)), "\n")
		files = append(files, untrackedFiles...)
	}
	
	// Remove duplicates and empty lines
	fileMap := make(map[string]bool)
	var result []string
	for _, file := range files {
		if file == "" {
			continue
		}
		if !fileMap[file] {
			fileMap[file] = true
			result = append(result, file)
		}
	}
	
	return result, nil
}

// New command for adding comments to issues
var issueCommentCmd = &cobra.Command{
	Use:   "comment [issue number]",
	Short: "Add a comment to a GitHub issue",
	Long:  `Add a comment to a specific GitHub issue, optionally with AI assistance.`,
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
		
		// Check authentication
		_, err = auth.Client()
		if err != nil {
			fmt.Println(color.RedString("Error:"), "GitHub authentication not configured. Please configure it with 'noidea config github-auth'")
			return
		}
		
		// Get comment body
		commentBody, _ := cmd.Flags().GetString("body")
		useAI, _ := cmd.Flags().GetBool("ai")
		fileRefs, _ := cmd.Flags().GetStringSlice("files")
		
		// Collect file references
		codeRefs := make(map[string]string)
		for _, filePath := range fileRefs {
			content, err := os.ReadFile(filePath)
			if err != nil {
				fmt.Println(color.YellowString("Warning:"), "Could not read file", filePath, ":", err)
				continue
			}
			codeRefs[filePath] = string(content)
		}
		
		// If AI is requested, generate a comment
		if useAI {
			if commentBody == "" {
				// Interactive mode for AI comment
				reader := bufio.NewReader(os.Stdin)
				fmt.Println("What would you like to comment about? (end with an empty line)")
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
				commentBody = bodyBuilder.String()
			}
			
			if commentBody == "" {
				fmt.Println(color.RedString("Error:"), "Comment description is required")
				return
			}
			
			// Generate AI comment
			fmt.Println(color.CyanString("Generating comment..."))
			commentBody = generateCommentWithAI(commentBody, issueNumber, repo)
			
			// Add file references to the comment
			for filePath := range codeRefs {
				if !strings.Contains(commentBody, fmt.Sprintf("{file:%s}", filePath)) {
					commentBody += fmt.Sprintf("\n\nReference to file {file:%s}", filePath)
				}
			}
			
			// Display the generated comment
			fmt.Println(color.CyanString("\nGenerated Comment:"))
			fmt.Println(commentBody)
			
			// Ask for confirmation
			reader := bufio.NewReader(os.Stdin)
			fmt.Print(color.CyanString("\nAdd this comment? [Y/n]: "))
			confirm, _ := reader.ReadString('\n')
			confirm = strings.TrimSpace(strings.ToLower(confirm))
			
			if confirm == "n" || confirm == "no" {
				fmt.Println(color.YellowString("Comment cancelled"))
				return
			}
		}
		
		// Check if we have a comment body
		if commentBody == "" {
			// Interactive mode for manual comment
			reader := bufio.NewReader(os.Stdin)
			fmt.Println("Enter your comment (end with an empty line):")
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
			commentBody = bodyBuilder.String()
			
			if commentBody == "" {
				fmt.Println(color.RedString("Error:"), "Comment body is required")
				return
			}
		}
		
		// Create issue service and add comment
		issueService := github.NewIssueService(auth)
		err = issueService.AddCommentWithCodeRefs(repo.Owner, repo.Name, issueNumber, commentBody, codeRefs)
		if err != nil {
			fmt.Println(color.RedString("Error:"), err)
			return
		}
		
		fmt.Println(color.GreenString("Comment added successfully to issue #%d", issueNumber))
	},
}

// generateCommentWithAI uses AI to generate a comment for an issue
func generateCommentWithAI(description string, issueNumber int, repo *github.RepoInfo) string {
	// Load configuration
	cfg := config.LoadConfig()
	
	// Check if LLM is enabled
	if !cfg.LLM.Enabled {
		// Just return the original text if AI is not enabled
		return description
	}
	
	// Get the issue details for context
	auth := github.NewAuthenticator()
	issueService := github.NewIssueService(auth)
	issue, err := issueService.GetIssue(repo.Owner, repo.Name, issueNumber)
	if err != nil {
		// If we can't get the issue, just return the description
		return description
	}
	
	// Define custom personality for comment creation
	commentPersonality := personality.Personality{
		Name:        "comment_creator",
		Description: "GitHub Issue Comment Creator",
		SystemPrompt: `You are a helpful assistant that creates well-formed GitHub issue comments.
Your comments should be clear, concise, and professional.
If code snippets are referenced, incorporate them meaningfully into your response.
Focus on being helpful and constructive.`,
		UserPromptFormat: fmt.Sprintf(`Create a GitHub issue comment based on this input:

%s

This comment is for Issue #%d: %s

Issue description:
%s

Create a well-structured comment that addresses the input and provides helpful information.
Use markdown formatting for clarity.`, 
			description, issueNumber, issue.Title, issue.Body),
		MaxTokens:   1000,
		Temperature: 0.7,
	}
	
	// Create a specialized engine with the comment personality
	commentEngine := feedback.NewFeedbackEngineWithCustomPersonality(
		cfg.LLM.Provider,
		cfg.LLM.Model,
		cfg.LLM.APIKey,
		commentPersonality,
	)
	
	// Create context with description
	ctx := feedback.CommitContext{
		Message:   description,
		Timestamp: time.Now(),
	}
	
	// Generate AI response
	aiResponse, err := commentEngine.GenerateFeedback(ctx)
	if err != nil {
		return description + "\n\n_Note: AI comment generation was attempted but failed._"
	}
	
	// Add signature
	aiResponse += "\n\n_Generated with noidea CLI_"
	
	return aiResponse
}

// generateSimpleIssueTemplate creates a basic issue template without AI
func generateSimpleIssueTemplate(description string, repo *github.RepoInfo) (string, string) {
	// Create a simple title from the first line of the description
	firstLine := strings.Split(description, "\n")[0]
	title := firstLine
	
	// Ensure title isn't too long
	if len(title) > 60 {
		title = title[:57] + "..."
	}
	
	// Extract key information from the description
	descLower := strings.ToLower(description)
	
	// Parse the description to extract details for the template sections
	var expectedBehavior, currentBehavior, possibleSolution, stepsToReproduce string
	
	// Check if this is related to any specific features from our roadmap
	isPluginSystem := strings.Contains(descLower, "plugin system") || strings.Contains(descLower, "plugin interface")
	isGithubProjects := strings.Contains(descLower, "github project") || strings.Contains(descLower, "project board")
	isLocalCache := strings.Contains(descLower, "local cache") || strings.Contains(descLower, "sqlite") || strings.Contains(descLower, "syncing")
	isWorkflow := strings.Contains(descLower, "workflow") || strings.Contains(descLower, "branch") || strings.Contains(descLower, "commit linking")
	isVersioning := strings.Contains(descLower, "version") || strings.Contains(descLower, "semantic") || strings.Contains(descLower, "release")
	
	// Check if this is a bug or feature
	isBug := strings.Contains(descLower, "bug") || strings.Contains(descLower, "fix") || 
		strings.Contains(descLower, "issue") || strings.Contains(descLower, "problem") ||
		strings.Contains(descLower, "error") || strings.Contains(descLower, "crash") ||
		strings.Contains(descLower, "doesn't work") || strings.Contains(descLower, "does not work") ||
		strings.Contains(descLower, "broken")
	
	// Default values
	expectedBehavior = "When this feature is implemented, the system should be able to:\n" +
		"- Support the functionality described in the description\n" +
		"- Integrate seamlessly with existing components\n" +
		"- Provide a user-friendly interface for this capability"
	
	currentBehavior = "Currently, this functionality is not implemented or doesn't meet the requirements described."
	
	possibleSolution = "Consider implementing this feature by:\n" +
		"- Creating the necessary interfaces and classes\n" +
		"- Integrating with existing systems\n" +
		"- Following the established patterns in the codebase\n" +
		"- Adding appropriate tests and documentation"
	
	stepsToReproduce = "1. Design the solution based on requirements\n" +
		"2. Implement the core functionality\n" +
		"3. Add tests and documentation\n" +
		"4. Submit for review"
	
	// Add specific content based on the type of issue
	if isPluginSystem {
		expectedBehavior = "When implemented, the Plugin System Foundation should:\n" +
			"- Support loading and unloading of plugins at runtime\n" +
			"- Provide well-defined interfaces for plugins to implement\n" +
			"- Include a discovery mechanism for finding available plugins\n" +
			"- Ensure plugins can't compromise the core application's stability\n" +
			"- Include documentation and examples for plugin creators"

		currentBehavior = "Currently, the application has no plugin system in place. All functionality is built directly into the application with no extension points."
		
		possibleSolution = "Implement the plugin system by:\n" +
			"- Creating an `internal/plugin` package with interface definitions\n" +
			"- Defining a standard plugin manifest format (JSON or YAML)\n" +
			"- Implementing a plugin loader that can dynamically load Go plugins or process scripts\n" +
			"- Adding a plugin registry to track loaded plugins\n" +
			"- Creating hooks in the application for plugins to integrate with\n" +
			"- Providing a sandboxing mechanism for plugin execution"
		
		stepsToReproduce = "1. Define plugin interfaces in a new `internal/plugin` package\n" +
			"2. Implement the plugin loading and registration system\n" +
			"3. Create extension points in the application code\n" +
			"4. Add plugin management commands to the CLI\n" +
			"5. Create documentation and example plugins\n" +
			"6. Add tests for the plugin system"
	} else if isGithubProjects {
		expectedBehavior = "When implemented, the GitHub Projects integration should:\n" +
			"- Display project boards and their columns within the CLI\n" +
			"- Allow moving cards between columns\n" +
			"- Support creating new project boards\n" +
			"- Provide filtering and search capabilities\n" +
			"- Integrate with the existing issue management system"
		
		currentBehavior = "Currently, the application can manage GitHub issues but has no integration with GitHub Projects. Users need to use the GitHub website to manage project boards."
		
		possibleSolution = "Implement GitHub Projects integration by:\n" +
			"- Extending the GitHub API client to support Projects API endpoints\n" +
			"- Creating models for Project boards, columns, and cards\n" +
			"- Adding commands for viewing and managing projects\n" +
			"- Implementing local caching of project data\n" +
			"- Creating a TUI interface for visualizing project boards"
		
		stepsToReproduce = "1. Extend the GitHub API client with Projects API support\n" +
			"2. Create data models for projects in `internal/github`\n" +
			"3. Implement commands for project management\n" +
			"4. Add project visualization in the CLI\n" +
			"5. Integrate with existing issue commands\n" +
			"6. Add tests for the new functionality"
	} else if isLocalCache {
		expectedBehavior = "When implemented, the Local Cache and Syncing system should:\n" +
			"- Store GitHub issues and related data in a local SQLite database\n" +
			"- Provide faster access to issue data without API calls\n" +
			"- Periodically sync with GitHub to keep data fresh\n" +
			"- Support offline operation with later synchronization\n" +
			"- Handle conflict resolution when local and remote data diverge"
		
		currentBehavior = "Currently, the application makes API calls to GitHub for each operation, which can be slow and requires constant internet connectivity. No data is cached locally between sessions."
		
		possibleSolution = "Implement the local cache by:\n" +
			"- Creating a new `internal/db` package for database operations\n" +
			"- Using SQLite as the storage backend\n" +
			"- Implementing models and schema for issues, comments, and projects\n" +
			"- Adding a synchronization service that runs periodically\n" +
			"- Modifying the GitHub service to use local data first\n" +
			"- Adding conflict detection and resolution mechanisms"
		
		stepsToReproduce = "1. Design the database schema for issues and related entities\n" +
			"2. Implement the database access layer in `internal/db`\n" +
			"3. Create the sync service to keep local and remote data in sync\n" +
			"4. Modify the GitHub service to use the cache\n" +
			"5. Add conflict resolution logic\n" +
			"6. Create tests for the caching and syncing functionality"
	} else if isWorkflow {
		expectedBehavior = "When implemented, the Workflow integration should:\n" +
			"- Create branches with standardized naming based on issues\n" +
			"- Automatically transition issues when branches are created/merged\n" +
			"- Link commits to related issues\n" +
			"- Update issue status based on commit messages\n" +
			"- Provide a seamless workflow from issue creation to closure"
		
		currentBehavior = "Currently, there's no automated workflow between Git operations and GitHub issues. Users must manually create branches, reference issues, and update issue status."
		
		possibleSolution = "Implement the workflow integration by:\n" +
			"- Creating a new `internal/workflow` package\n" +
			"- Implementing branch naming conventions and generators\n" +
			"- Adding Git hooks for commit message validation and issue linking\n" +
			"- Creating a state machine for issue transitions\n" +
			"- Enhancing the commit hook to detect issue references\n" +
			"- Adding workflow commands to the CLI"
		
		stepsToReproduce = "1. Design the workflow state machine and transitions\n" +
			"2. Implement branch naming and creation in `internal/workflow`\n" +
			"3. Create Git hooks for commit message processing\n" +
			"4. Add issue transition logic\n" +
			"5. Implement commands for workflow management\n" +
			"6. Add tests for the workflow functionality"
	} else if isVersioning {
		expectedBehavior = "When implemented, the Semantic Versioning system should:\n" +
			"- Follow semantic versioning principles (MAJOR.MINOR.PATCH)\n" +
			"- Automate version bumps based on commit types\n" +
			"- Generate changelogs from commit messages\n" +
			"- Create proper release tags\n" +
			"- Display version information in the CLI\n" +
			"- Add version badges to documentation"
		
		currentBehavior = "Currently, there's no standardized versioning system in place. Version numbers are manually updated and there's no automated changelog generation."
		
		possibleSolution = "Implement the semantic versioning by:\n" +
			"- Creating version parsing and manipulation utilities\n" +
			"- Adding commit message conventions (possibly using Conventional Commits)\n" +
			"- Implementing changelog generation from Git history\n" +
			"- Adding release commands to the CLI\n" +
			"- Creating GitHub Actions for automated releases\n" +
			"- Adding version display to the CLI"
		
		stepsToReproduce = "1. Define commit message conventions\n" +
			"2. Implement version parsing and bumping logic\n" +
			"3. Create changelog generation functionality\n" +
			"4. Add release commands to the CLI\n" +
			"5. Implement GitHub Actions workflows for releases\n" +
			"6. Add tests for versioning functionality"
	} else if isBug {
		expectedBehavior = "The system should function correctly without the issues described in the description."
		currentBehavior = "The system currently exhibits problems as described in the description."
		stepsToReproduce = "1. Identify the root cause of the issue\n" +
			"2. Implement a fix that addresses the core problem\n" +
			"3. Add tests to prevent regression\n" +
			"4. Submit for review"
	}
	
	// Generate template with sections
	body := fmt.Sprintf(`## Description

%s

## Expected Behavior

%s

## Current Behavior

%s

## Possible Solution

%s

## Steps to Reproduce

%s

## Environment

- Repository: %s/%s
- Generated with noidea CLI`, description, expectedBehavior, currentBehavior, possibleSolution, stepsToReproduce, repo.Owner, repo.Name)
	
	return title, body
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