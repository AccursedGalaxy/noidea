package feedback

import (
	"context"
	"fmt"
	"os/exec"
	"strings"

	"github.com/AccursedGalaxy/noidea/internal/personality"
	openai "github.com/sashabaranov/go-openai"
)

// ProviderConfig contains configuration for different LLM providers
type ProviderConfig struct {
	BaseURL      string
	DefaultModel string
	Name         string
}

// Known providers
var (
	ProviderXAI = ProviderConfig{
		BaseURL:      "https://api.x.ai/v1",
		DefaultModel: "grok-2-1212",
		Name:         "xAI",
	}
	
	ProviderOpenAI = ProviderConfig{
		BaseURL:      "", // Default OpenAI URL
		DefaultModel: "gpt-3.5-turbo",
		Name:         "OpenAI",
	}
	
	ProviderDeepSeek = ProviderConfig{
		BaseURL:      "https://api.deepseek.com/v1", // This is a placeholder, replace with actual URL
		DefaultModel: "deepseek-chat",
		Name:         "DeepSeek",
	}
)

// UnifiedFeedbackEngine generates feedback using any OpenAI-compatible API
type UnifiedFeedbackEngine struct {
	client        *openai.Client
	model         string
	provider      ProviderConfig
	personalityName string
	personalityFile string
}

// NewUnifiedFeedbackEngine creates a new unified feedback engine
func NewUnifiedFeedbackEngine(provider string, model string, apiKey string, personalityName string, personalityFile string) *UnifiedFeedbackEngine {
	var providerConfig ProviderConfig
	
	// Select provider configuration
	switch provider {
	case "xai":
		providerConfig = ProviderXAI
	case "openai":
		providerConfig = ProviderOpenAI
	case "deepseek":
		providerConfig = ProviderDeepSeek
	default:
		// Default to OpenAI if unknown provider
		providerConfig = ProviderOpenAI
	}
	
	// Use provider's default model if none specified
	if model == "" {
		model = providerConfig.DefaultModel
	}
	
	// Configure the client
	config := openai.DefaultConfig(apiKey)
	if providerConfig.BaseURL != "" {
		config.BaseURL = providerConfig.BaseURL
	}
	
	client := openai.NewClientWithConfig(config)
	return &UnifiedFeedbackEngine{
		client:        client,
		model:         model,
		provider:      providerConfig,
		personalityName: personalityName,
		personalityFile: personalityFile,
	}
}

// GenerateFeedback implements the FeedbackEngine interface
func (e *UnifiedFeedbackEngine) GenerateFeedback(ctx CommitContext) (string, error) {
	// Load personality configuration
	personalities, err := personality.LoadPersonalities(e.personalityFile)
	if err != nil {
		// Fall back to default personalities if there's an error
		personalities = personality.DefaultPersonalities()
	}

	// Get the selected personality
	personalityConfig, err := personalities.GetPersonality(e.personalityName)
	if err != nil {
		// Fall back to default personality
		personalityConfig, _ = personalities.GetPersonality("")
	}

	// Create personality context for template rendering
	personalityCtx := personality.Context{
		Message:       ctx.Message,
		TimeOfDay:     GetTimeOfDay(ctx.Timestamp),
		Diff:          ctx.Diff,
		Username:      getUserName(),
		RepoName:      getRepoName(),
		CommitHistory: ctx.CommitHistory,
		CommitStats:   ctx.CommitStats,
	}

	// Generate the prompt using the personality template
	userPrompt, err := personalityConfig.GeneratePrompt(personalityCtx)
	if err != nil {
		return "", fmt.Errorf("failed to generate prompt: %w", err)
	}

	// Create the chat completion request
	request := openai.ChatCompletionRequest{
		Model: e.model,
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleSystem,
				Content: personalityConfig.SystemPrompt,
			},
			{
				Role:    openai.ChatMessageRoleUser,
				Content: userPrompt,
			},
		},
		Temperature: float32(personalityConfig.Temperature),
		MaxTokens:   personalityConfig.MaxTokens,
		N:           1,
	}

	// Send the request to the API
	response, err := e.client.CreateChatCompletion(context.Background(), request)
	if err != nil {
		return "", fmt.Errorf("%s API error: %w", e.provider.Name, err)
	}

	// Extract the response content
	if len(response.Choices) > 0 {
		return response.Choices[0].Message.Content, nil
	}

	return "", fmt.Errorf("no response from %s API", e.provider.Name)
}

// GenerateSummaryFeedback provides insights for a weekly summary or on-demand analysis
func (e *UnifiedFeedbackEngine) GenerateSummaryFeedback(ctx CommitContext) (string, error) {
	// Load personality configuration
	personalities, err := personality.LoadPersonalities(e.personalityFile)
	if err != nil {
		// Fall back to default personalities if there's an error
		personalities = personality.DefaultPersonalities()
	}

	// Get the selected personality
	personalityConfig, err := personalities.GetPersonality(e.personalityName)
	if err != nil {
		// Fall back to default personality
		personalityConfig, _ = personalities.GetPersonality("")
	}

	// Create a custom system prompt for summaries or on-demand feedback
	systemPrompt := personalityConfig.SystemPrompt
	if strings.Contains(systemPrompt, "one-liner") || strings.Contains(systemPrompt, "one sentence") {
		// Determine if this is a weekly summary or on-demand feedback
		isOnDemand := strings.Contains(ctx.Message, "On-Demand")
		
		if isOnDemand {
			// Specialized prompt for targeted code analysis
			systemPrompt = `You are an insightful Git expert who analyzes code practices and commit patterns.
Your task is to provide targeted, actionable feedback on the specific set of commits being reviewed.
Focus on identifying patterns, potential issues, and specific suggestions for improvement.
Consider best practices related to commit message quality, code organization, and development workflow.
Your response should be 2-4 paragraphs with useful observations and actionable recommendations.
If diffs are provided, focus your analysis on the actual code changes too.`
		} else {
			// Original weekly summary prompt
			systemPrompt = `You are an insightful Git expert who analyzes commit patterns.
Provide a thoughtful, detailed analysis of the commit history.
Focus on patterns, trends, and actionable insights.
Your response should be 3-5 paragraphs with useful observations and suggestions.`
		}
	}

	// Determine the appropriate user prompt based on context
	var userPrompt string
	isOnDemand := strings.Contains(ctx.Message, "On-Demand")
	
	if isOnDemand {
		// Specialized prompt for on-demand feedback
		userPrompt = fmt.Sprintf(`I'd like you to analyze this specific set of Git commits.

Commit messages:
%s

Commit statistics:
- Total commits: %v
- Files changed: %v
- Lines added: %v
- Lines deleted: %v

%s

Please provide targeted feedback about:
1. Code quality patterns visible in these commits
2. Commit message quality and clarity
3. Specific suggestions for improvement
4. Best practices that could be applied

Focus on giving actionable, specific feedback for these particular commits:`,
			formatCommitList(ctx.CommitHistory),
			ctx.CommitStats["total_commits"],
			ctx.CommitStats["total_files_changed"],
			ctx.CommitStats["total_insertions"],
			ctx.CommitStats["total_deletions"],
			diffContext(ctx.Diff))
	} else {
		// Original weekly summary prompt
		userPrompt = fmt.Sprintf(`I'd like you to analyze my Git commit history from the past week.

Commit messages:
%s

Commit statistics:
- Total commits: %v
- Unique authors: %v
- Files changed: %v
- Lines added: %v
- Lines deleted: %v

Please provide insights about:
1. Commit message patterns and quality
2. Work focus areas (based on commit messages)
3. Time distribution patterns
4. Suggestions for improving workflow or commit habits

Respond with thoughtful analysis and actionable suggestions:`,
			formatCommitList(ctx.CommitHistory),
			ctx.CommitStats["total_commits"],
			ctx.CommitStats["unique_authors"],
			ctx.CommitStats["total_files_changed"],
			ctx.CommitStats["total_insertions"],
			ctx.CommitStats["total_deletions"])
	}

	// Create the chat completion request
	request := openai.ChatCompletionRequest{
		Model: e.model,
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleSystem,
				Content: systemPrompt,
			},
			{
				Role:    openai.ChatMessageRoleUser,
				Content: userPrompt,
			},
		},
		Temperature: float32(personalityConfig.Temperature),
		MaxTokens:   800, // Increase token limit for more detailed analysis
		N:           1,
	}

	// Send the request to the API
	response, err := e.client.CreateChatCompletion(context.Background(), request)
	if err != nil {
		return "", fmt.Errorf("%s API error: %w", e.provider.Name, err)
	}

	// Extract the response content
	if len(response.Choices) > 0 {
		return response.Choices[0].Message.Content, nil
	}

	return "", fmt.Errorf("no response from %s API", e.provider.Name)
}

// GenerateCommitSuggestion creates an AI-generated commit message based on staged changes
func (e *UnifiedFeedbackEngine) GenerateCommitSuggestion(ctx CommitContext) (string, error) {
	// Load personality configuration - only needed for fallback, not for styling
	personalities, err := personality.LoadPersonalities(e.personalityFile)
	if err != nil {
		// Fall back to default personalities if there's an error
		personalities = personality.DefaultPersonalities()
	}

	// Get the selected personality - we'll only use this for basic functionality
	_, err = personalities.GetPersonality(e.personalityName)
	if err != nil {
		// Just make sure we have a valid personality, but won't use its styling
		_, _ = personalities.GetPersonality("")
	}

	// Use a custom system prompt focused on commit message generation
	// This override ensures professional commit messages regardless of personality
	systemPrompt := `You are a Git expert who writes clear, concise, and descriptive commit messages.
Your task is to suggest a high-quality commit message based on the staged changes.
Follow these guidelines:
1. IMPORTANT: Focus primarily on the ACTUAL CHANGES in the diff, not on past commit patterns
2. When changes span MULTIPLE CATEGORIES (docs, code, build files, etc.), make sure to reflect ALL major aspects
3. Use the conventional commits format (type: description) when appropriate
   - docs: for documentation changes
   - feat: for new features
   - fix: for bug fixes
   - refactor: for code restructuring without behavior changes
   - style: for formatting/style changes
   - test: for adding or fixing tests
   - chore: for routine maintenance tasks
   - build: for changes to build system or dependencies
4. For mixed changes, choose the most significant type or use a broader scope like "feat" or "chore"
5. When changes involve multiple components use a scope that encompasses all of them (e.g., "build+docs")
6. Be specific about what changed, making sure your message accurately reflects the actual modifications
7. Keep the first line under 72 characters
8. Use present tense (e.g., "add feature" not "added feature")
9. IMPORTANT: Your response must ONLY contain the commit message itself, with no explanations, reasoning, or markdown formatting`

	// Prepare the diff context - enhanced with file analysis
	diffContext := `
Here's the current diff of staged changes:

` + ctx.Diff + `

Analysis of changes:
`
	
	// Add simple analysis of the types of files changed and how many lines were modified
	var totalAdditions, totalDeletions int
	changedFiles := make(map[string]bool)
	
	// Track different types of files
	docFiles := make(map[string]bool)     // Documentation files (.md, .txt, etc)
	codeFiles := make(map[string]bool)    // Source code files (.go, .js, etc)
	configFiles := make(map[string]bool)  // Configuration files (.json, .yaml, etc)
	buildFiles := make(map[string]bool)   // Build files (Makefile, CMakeLists.txt, etc)
	testFiles := make(map[string]bool)    // Test files (*_test.go, etc)
	scriptFiles := make(map[string]bool)  // Scripts (.sh, .bat, etc)
	
	// Track file operations
	addedFiles := make(map[string]bool)
	modifiedFiles := make(map[string]bool)
	deletedFiles := make(map[string]bool)
	
	// Simple diff parser to count lines and identify files
	lines := strings.Split(ctx.Diff, "\n")
	currentFile := ""
	
	for _, line := range lines {
		if strings.HasPrefix(line, "diff --git") {
			parts := strings.Fields(line)
			if len(parts) >= 3 {
				filePath := strings.TrimPrefix(parts[2], "a/")
				currentFile = filePath
				changedFiles[filePath] = true
				
				// Categorize by file type
				switch {
				case strings.HasSuffix(filePath, ".md"), strings.HasSuffix(filePath, ".txt"), strings.HasSuffix(filePath, ".rst"):
					docFiles[filePath] = true
				case strings.HasSuffix(filePath, ".go"), strings.HasSuffix(filePath, ".js"), strings.HasSuffix(filePath, ".ts"), 
				     strings.HasSuffix(filePath, ".py"), strings.HasSuffix(filePath, ".java"), strings.HasSuffix(filePath, ".c"), 
				     strings.HasSuffix(filePath, ".cpp"), strings.HasSuffix(filePath, ".h"):
					if strings.Contains(filePath, "_test.") {
						testFiles[filePath] = true
					} else {
						codeFiles[filePath] = true
					}
				case strings.HasSuffix(filePath, ".json"), strings.HasSuffix(filePath, ".yaml"), strings.HasSuffix(filePath, ".yml"),
				     strings.HasSuffix(filePath, ".toml"), strings.HasSuffix(filePath, ".ini"), strings.HasSuffix(filePath, ".config"):
					configFiles[filePath] = true
				case strings.HasSuffix(filePath, "Makefile"), strings.HasSuffix(filePath, ".mk"), 
				     strings.Contains(filePath, "CMakeLists.txt"), strings.HasSuffix(filePath, ".bazel"):
					buildFiles[filePath] = true
				case strings.HasSuffix(filePath, ".sh"), strings.HasSuffix(filePath, ".bash"), 
				     strings.HasSuffix(filePath, ".bat"), strings.HasSuffix(filePath, ".ps1"):
					scriptFiles[filePath] = true
				}
			}
		} else if strings.HasPrefix(line, "new file mode") {
			addedFiles[currentFile] = true
		} else if strings.HasPrefix(line, "deleted file mode") {
			deletedFiles[currentFile] = true
		} else if !deletedFiles[currentFile] && !addedFiles[currentFile] {
			modifiedFiles[currentFile] = true
		}
		
		if strings.HasPrefix(line, "+") && !strings.HasPrefix(line, "+++") {
			totalAdditions++
		} else if strings.HasPrefix(line, "-") && !strings.HasPrefix(line, "---") {
			totalDeletions++
		}
	}
	
	// Remove files from modified if they're added or deleted
	for file := range addedFiles {
		delete(modifiedFiles, file)
	}
	for file := range deletedFiles {
		delete(modifiedFiles, file)
	}
	
	// Format the analysis
	diffContext += fmt.Sprintf("- Total files changed: %d (%d added, %d modified, %d deleted)\n", 
		len(changedFiles), len(addedFiles), len(modifiedFiles), len(deletedFiles))
	diffContext += fmt.Sprintf("- Lines: +%d, -%d\n\n", totalAdditions, totalDeletions)
	
	// Add file categories analysis
	if len(docFiles) > 0 {
		fileList := make([]string, 0, len(docFiles))
		for file := range docFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Documentation files: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(codeFiles) > 0 {
		fileList := make([]string, 0, len(codeFiles))
		for file := range codeFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Code files: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(buildFiles) > 0 {
		fileList := make([]string, 0, len(buildFiles))
		for file := range buildFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Build files: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(scriptFiles) > 0 {
		fileList := make([]string, 0, len(scriptFiles))
		for file := range scriptFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Script files: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(configFiles) > 0 {
		fileList := make([]string, 0, len(configFiles))
		for file := range configFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Config files: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(testFiles) > 0 {
		fileList := make([]string, 0, len(testFiles))
		for file := range testFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Test files: %s\n", strings.Join(fileList, ", "))
	}
	
	// Add operations analysis
	diffContext += "\nFile operations:\n"
	
	if len(addedFiles) > 0 {
		fileList := make([]string, 0, len(addedFiles))
		for file := range addedFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Added: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(modifiedFiles) > 0 {
		fileList := make([]string, 0, len(modifiedFiles))
		for file := range modifiedFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Modified: %s\n", strings.Join(fileList, ", "))
	}
	
	if len(deletedFiles) > 0 {
		fileList := make([]string, 0, len(deletedFiles))
		for file := range deletedFiles {
			fileList = append(fileList, file)
		}
		diffContext += fmt.Sprintf("Deleted: %s\n", strings.Join(fileList, ", "))
	}

	// Create a user prompt focused on commit message generation with emphasis on changes
	userPrompt := fmt.Sprintf(`I need a commit message for these staged changes.

%s

Past commit messages for limited context (do not rely heavily on these patterns):
%s

Based primarily on the ACTUAL CHANGES shown above, suggest a concise, descriptive commit message that accurately describes what was modified:`,
		diffContext,
		formatCommitList(ctx.CommitHistory))

	// Create the chat completion request
	request := openai.ChatCompletionRequest{
		Model: e.model,
		Messages: []openai.ChatCompletionMessage{
			{
				Role:    openai.ChatMessageRoleSystem,
				Content: systemPrompt,
			},
			{
				Role:    openai.ChatMessageRoleUser,
				Content: userPrompt,
			},
		},
		Temperature: 0.3, // Fixed lower temperature for more precise, professional responses
		MaxTokens:   150, // Commit messages are short
		N:           1,
	}

	// Send the request to the API
	response, err := e.client.CreateChatCompletion(context.Background(), request)
	if err != nil {
		return "", fmt.Errorf("%s API error: %w", e.provider.Name, err)
	}

	// Extract the response content
	if len(response.Choices) > 0 {
		// Get the raw response
		rawSuggestion := response.Choices[0].Message.Content
		
		// Clean up the response and extract only the actual commit message
		suggestion := extractCommitMessage(rawSuggestion)
		
		return suggestion, nil
	}

	return "", fmt.Errorf("no response from %s API", e.provider.Name)
}

// extractCommitMessage parses the LLM response to extract just the commit message
func extractCommitMessage(response string) string {
	// Trim whitespace
	response = strings.TrimSpace(response)
	
	// If wrapped in quotes, remove them
	if strings.HasPrefix(response, "\"") && strings.HasSuffix(response, "\"") {
		response = response[1 : len(response)-1]
	}
	
	// Check if the response contains a code block with ```
	if strings.Contains(response, "```") {
		// Extract content between code blocks
		parts := strings.Split(response, "```")
		if len(parts) >= 3 {
			// The code block content is in the even indices (1, 3, etc.)
			response = strings.TrimSpace(parts[1])
		}
	}
	
	// Check if there are multiple lines with a conventional commit format on one line
	lines := strings.Split(response, "\n")
	for _, line := range lines {
		// Look for lines that match conventional commit format (type: message)
		line = strings.TrimSpace(line)
		if strings.Contains(line, ":") && len(line) < 100 {
			typePrefix := strings.Split(line, ":")[0]
			// Common commit types
			commitTypes := []string{"feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"}
			for _, cType := range commitTypes {
				if typePrefix == cType {
					return line
				}
			}
		}
	}
	
	// If we couldn't extract a specific format, return the first non-empty line
	// that is reasonable length for a commit message
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line != "" && len(line) < 100 && !strings.HasPrefix(line, "#") {
			return line
		}
	}
	
	// If all else fails, return the first 72 chars of first line
	if len(lines) > 0 {
		firstLine := strings.TrimSpace(lines[0])
		if len(firstLine) > 72 {
			return firstLine[:72]
		}
		return firstLine
	}
	
	return response
}

// formatCommitList creates a formatted string of commit messages
func formatCommitList(commits []string) string {
	var result strings.Builder
	
	for i, commit := range commits {
		result.WriteString(fmt.Sprintf("%d. %s\n", i+1, commit))
	}
	
	return result.String()
}

// getUserName attempts to get the Git user name
func getUserName() string {
	cmd := exec.Command("git", "config", "user.name")
	output, err := cmd.Output()
	if err != nil {
		return "User"
	}
	return strings.TrimSpace(string(output))
}

// getRepoName attempts to get the Git repository name
func getRepoName() string {
	// Try to get the remote origin URL
	cmd := exec.Command("git", "config", "--get", "remote.origin.url")
	output, err := cmd.Output()
	if err != nil {
		return "repository"
	}

	// Extract repo name from URL
	repoURL := strings.TrimSpace(string(output))
	parts := strings.Split(repoURL, "/")
	if len(parts) > 0 {
		repoName := parts[len(parts)-1]
		// Remove .git suffix if present
		repoName = strings.TrimSuffix(repoName, ".git")
		return repoName
	}

	return "repository"
}

// diffContext formats diff context for the prompt
func diffContext(diff string) string {
	if diff == "" {
		return ""
	}
	
	return fmt.Sprintf(`Code changes (diff context):
%s`, diff)
}