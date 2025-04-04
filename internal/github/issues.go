package github

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/google/go-github/v54/github"
)

// IssueService provides operations for GitHub issues
type IssueService struct {
	auth *Authenticator
}

// NewIssueService creates a new GitHub issue service
func NewIssueService(auth *Authenticator) *IssueService {
	return &IssueService{
		auth: auth,
	}
}

// Issue represents a GitHub issue with relevant fields
type Issue struct {
	Number      int
	Title       string
	Body        string
	State       string
	URL         string
	CreatedAt   time.Time
	UpdatedAt   time.Time
	Author      string
	Assignees   []string
	Labels      []string
	Milestone   string
	Comments    int
	IsOpen      bool
	Repository  string
	ProjectCard string
}

// convertGitHubIssue converts a GitHub issue to our internal format
func convertGitHubIssue(ghIssue *github.Issue) Issue {
	issue := Issue{
		Number:    *ghIssue.Number,
		Title:     *ghIssue.Title,
		State:     *ghIssue.State,
		URL:       *ghIssue.HTMLURL,
		CreatedAt: ghIssue.CreatedAt.Time,
		UpdatedAt: ghIssue.UpdatedAt.Time,
		Comments:  *ghIssue.Comments,
		IsOpen:    *ghIssue.State == "open",
	}
	
	// Handle optional fields
	if ghIssue.Body != nil {
		issue.Body = *ghIssue.Body
	}
	
	if ghIssue.User != nil && ghIssue.User.Login != nil {
		issue.Author = *ghIssue.User.Login
	}
	
	// Extract assignees
	for _, assignee := range ghIssue.Assignees {
		if assignee.Login != nil {
			issue.Assignees = append(issue.Assignees, *assignee.Login)
		}
	}
	
	// Extract labels
	for _, label := range ghIssue.Labels {
		if label.Name != nil {
			issue.Labels = append(issue.Labels, *label.Name)
		}
	}
	
	// Extract milestone
	if ghIssue.Milestone != nil && ghIssue.Milestone.Title != nil {
		issue.Milestone = *ghIssue.Milestone.Title
	}
	
	return issue
}

// ListIssues retrieves issues for the current repository
func (s *IssueService) ListIssues(owner, repo string, state string, limit int) ([]Issue, error) {
	// Get authenticated client
	client, err := s.auth.Client()
	if err != nil {
		return nil, err
	}
	
	// Set up options
	opts := &github.IssueListByRepoOptions{
		State: state,
		ListOptions: github.ListOptions{
			PerPage: limit,
		},
	}
	
	// Call GitHub API
	ctx := context.Background()
	ghIssues, _, err := client.Issues.ListByRepo(ctx, owner, repo, opts)
	if err != nil {
		return nil, fmt.Errorf("failed to list issues: %w", err)
	}
	
	// Convert to our format
	issues := make([]Issue, 0, len(ghIssues))
	for _, ghIssue := range ghIssues {
		// Skip pull requests
		if ghIssue.IsPullRequest() {
			continue
		}
		
		issue := convertGitHubIssue(ghIssue)
		issue.Repository = fmt.Sprintf("%s/%s", owner, repo)
		issues = append(issues, issue)
	}
	
	return issues, nil
}

// GetIssue retrieves a specific issue
func (s *IssueService) GetIssue(owner, repo string, number int) (*Issue, error) {
	// Get authenticated client
	client, err := s.auth.Client()
	if err != nil {
		return nil, err
	}
	
	// Call GitHub API
	ctx := context.Background()
	ghIssue, _, err := client.Issues.Get(ctx, owner, repo, number)
	if err != nil {
		return nil, fmt.Errorf("failed to get issue #%d: %w", number, err)
	}
	
	// Convert to our format
	issue := convertGitHubIssue(ghIssue)
	issue.Repository = fmt.Sprintf("%s/%s", owner, repo)
	
	return &issue, nil
}

// CreateIssue creates a new issue
func (s *IssueService) CreateIssue(owner, repo, title, body string, labels []string) (*Issue, error) {
	// Get authenticated client
	client, err := s.auth.Client()
	if err != nil {
		return nil, err
	}
	
	// Create request
	req := &github.IssueRequest{
		Title: github.String(title),
		Body:  github.String(body),
	}
	
	// Add labels if provided
	if len(labels) > 0 {
		req.Labels = &labels
	}
	
	// Call GitHub API
	ctx := context.Background()
	ghIssue, resp, err := client.Issues.Create(ctx, owner, repo, req)
	if err != nil {
		if resp != nil {
			// Show detailed API error information
			return nil, fmt.Errorf("failed to create issue: %w (Status: %d, URL: %s)", 
				err, resp.StatusCode, resp.Request.URL)
		}
		return nil, fmt.Errorf("failed to create issue: %w", err)
	}
	
	// Convert to our format
	issue := convertGitHubIssue(ghIssue)
	issue.Repository = fmt.Sprintf("%s/%s", owner, repo)
	
	return &issue, nil
}

// CloseIssue closes an issue
func (s *IssueService) CloseIssue(owner, repo string, number int, comment string) error {
	// Get authenticated client
	client, err := s.auth.Client()
	if err != nil {
		return err
	}
	
	// If a comment is provided, add it first
	if comment != "" {
		// Create comment
		commentObj := &github.IssueComment{
			Body: github.String(comment),
		}
		
		// Call GitHub API to add comment
		ctx := context.Background()
		_, _, err = client.Issues.CreateComment(ctx, owner, repo, number, commentObj)
		if err != nil {
			return fmt.Errorf("failed to add closing comment to issue #%d: %w", number, err)
		}
	}
	
	// Create close request
	req := &github.IssueRequest{
		State: github.String("closed"),
	}
	
	// Call GitHub API
	ctx := context.Background()
	_, _, err = client.Issues.Edit(ctx, owner, repo, number, req)
	if err != nil {
		return fmt.Errorf("failed to close issue #%d: %w", number, err)
	}
	
	return nil
}

// AddComment adds a comment to an issue
func (s *IssueService) AddComment(owner, repo string, number int, body string) error {
	// Get authenticated client
	client, err := s.auth.Client()
	if err != nil {
		return err
	}
	
	// Create comment
	comment := &github.IssueComment{
		Body: github.String(body),
	}
	
	// Call GitHub API
	ctx := context.Background()
	_, _, err = client.Issues.CreateComment(ctx, owner, repo, number, comment)
	if err != nil {
		return fmt.Errorf("failed to add comment to issue #%d: %w", number, err)
	}
	
	return nil
}

// CreateIssueWithCodeRefs creates a new issue and processes code references in the body
// It will look for patterns like {file:path/to/file.ext} and replace them with the file contents
func (s *IssueService) CreateIssueWithCodeRefs(owner, repo, title, body string, labels []string, codeRefs map[string]string) (*Issue, error) {
	// Process code references if any are provided
	processedBody := body
	if len(codeRefs) > 0 {
		for ref, content := range codeRefs {
			placeholder := fmt.Sprintf("{file:%s}", ref)
			
			// Limit the amount of code included by applying intelligent trimming
			trimmedContent := trimCodeContent(content, ref)
			
			// Format the code with proper reference
			fileExt := getFileExtension(ref)
			var replacement string
			if fileExt != "" {
				replacement = fmt.Sprintf("Reference to file `%s`\n\n```%s\n// File: %s (extracted relevant portion)\n// NOTE: Large file - showing extracted portions only\n\n%s\n```", 
					ref, fileExt, ref, trimmedContent)
			} else {
				replacement = fmt.Sprintf("Reference to file `%s`\n\n```\n// File: %s (extracted relevant portion)\n// NOTE: Large file - showing extracted portions only\n\n%s\n```", 
					ref, ref, trimmedContent)
			}
			
			processedBody = strings.Replace(processedBody, placeholder, replacement, -1)
		}
	}
	
	// Create the issue with the processed body
	return s.CreateIssue(owner, repo, title, processedBody, labels)
}

// AddCommentWithCodeRefs adds a comment to an issue and processes code references
func (s *IssueService) AddCommentWithCodeRefs(owner, repo string, number int, body string, codeRefs map[string]string) error {
	// Process code references if any are provided
	processedBody := body
	if len(codeRefs) > 0 {
		for ref, content := range codeRefs {
			placeholder := fmt.Sprintf("{file:%s}", ref)
			
			// Limit the amount of code included by applying intelligent trimming
			trimmedContent := trimCodeContent(content, ref)
			
			// Format the code with proper reference and language hint
			fileExt := getFileExtension(ref)
			var replacement string
			if fileExt != "" {
				replacement = fmt.Sprintf("Reference to file `%s`\n\n```%s\n// File: %s (extracted relevant portion)\n// NOTE: Large file - showing extracted portions only\n\n%s\n```", 
					ref, fileExt, ref, trimmedContent)
			} else {
				replacement = fmt.Sprintf("Reference to file `%s`\n\n```\n// File: %s (extracted relevant portion)\n// NOTE: Large file - showing extracted portions only\n\n%s\n```", 
					ref, ref, trimmedContent)
			}
			
			processedBody = strings.Replace(processedBody, placeholder, replacement, -1)
		}
	}
	
	// Add the comment with the processed body
	return s.AddComment(owner, repo, number, processedBody)
}

// trimCodeContent intelligently trims code content to a reasonable size
// It attempts to extract the most relevant portions based on file type and content
func trimCodeContent(content, filePath string) string {
	// Split content into lines
	lines := strings.Split(content, "\n")
	
	// If the file is already small enough, just return it
	maxLines := 50 // Maximum number of lines to include
	if len(lines) <= maxLines {
		return content
	}
	
	// Extract file extension to determine language-specific handling
	fileExt := getFileExtension(filePath)
	
	// For Go files, try to extract functions/structs/interfaces
	if fileExt == "go" {
		return extractRelevantGoCode(lines, maxLines)
	}
	
	// For JavaScript/TypeScript, extract classes/functions
	if fileExt == "js" || fileExt == "ts" || fileExt == "jsx" || fileExt == "tsx" {
		return extractRelevantJSCode(lines, maxLines)
	}
	
	// Default strategy: take the first few lines, some middle lines, and last few lines
	return extractGeneralCodeSample(lines, maxLines)
}

// getFileExtension extracts the file extension from a path
func getFileExtension(filePath string) string {
	parts := strings.Split(filePath, ".")
	if len(parts) > 1 {
		return parts[len(parts)-1]
	}
	return ""
}

// extractRelevantGoCode tries to extract important parts of Go code
func extractRelevantGoCode(lines []string, maxLines int) string {
	var result []string
	
	// Add a header showing it's truncated
	result = append(result, "// NOTE: Large file - showing extracted portions only")
	result = append(result, "")
	
	// Try to find important structures (imports, structs, funcs)
	inImports := false
	inStruct := false
	inFunc := false
	
	importSection := []string{}
	structSections := [][]string{}
	funcSections := [][]string{}
	currentSection := []string{}
	
	for _, line := range lines {
		trimmedLine := strings.TrimSpace(line)
		
		// Track import section
		if strings.HasPrefix(trimmedLine, "import (") {
			inImports = true
			importSection = append(importSection, line)
			continue
		}
		if inImports {
			importSection = append(importSection, line)
			if trimmedLine == ")" {
				inImports = false
			}
			continue
		}
		
		// Track struct declarations
		if strings.HasPrefix(trimmedLine, "type ") && strings.Contains(line, "struct {") {
			inStruct = true
			currentSection = []string{line}
			continue
		}
		if inStruct {
			currentSection = append(currentSection, line)
			if trimmedLine == "}" {
				inStruct = false
				structSections = append(structSections, currentSection)
				currentSection = []string{}
			}
			continue
		}
		
		// Track function declarations
		if strings.HasPrefix(trimmedLine, "func ") {
			inFunc = true
			currentSection = []string{line}
			continue
		}
		if inFunc {
			currentSection = append(currentSection, line)
			if trimmedLine == "}" {
				inFunc = false
				funcSections = append(funcSections, currentSection)
				currentSection = []string{}
			}
			continue
		}
	}
	
	// Add imports if found
	if len(importSection) > 0 && len(importSection) < maxLines/4 {
		result = append(result, "// Package imports")
		result = append(result, importSection...)
		result = append(result, "")
	}
	
	// Add struct samples
	if len(structSections) > 0 {
		result = append(result, "// Sample struct definitions")
		// Take at most 2 structs
		numStructs := 2
		if len(structSections) < numStructs {
			numStructs = len(structSections)
		}
		for i := 0; i < numStructs; i++ {
			result = append(result, structSections[i]...)
			result = append(result, "")
		}
		if len(structSections) > numStructs {
			result = append(result, fmt.Sprintf("// ... and %d more struct definitions", len(structSections)-numStructs))
			result = append(result, "")
		}
	}
	
	// Add function samples
	if len(funcSections) > 0 {
		result = append(result, "// Sample function definitions")
		// Take at most 3 functions, preferring shorter ones
		sort.Slice(funcSections, func(i, j int) bool {
			return len(funcSections[i]) < len(funcSections[j])
		})
		
		numFuncs := 3
		if len(funcSections) < numFuncs {
			numFuncs = len(funcSections)
		}
		
		totalLines := 0
		for i := 0; i < numFuncs; i++ {
			if totalLines+len(funcSections[i]) > maxLines {
				break
			}
			result = append(result, funcSections[i]...)
			result = append(result, "")
			totalLines += len(funcSections[i]) + 1
		}
		
		if len(funcSections) > numFuncs {
			result = append(result, fmt.Sprintf("// ... and %d more functions", len(funcSections)-numFuncs))
		}
	}
	
	// If we couldn't extract structured elements, fall back to sample approach
	if len(result) < 5 {
		return extractGeneralCodeSample(lines, maxLines)
	}
	
	return strings.Join(result, "\n")
}

// extractRelevantJSCode tries to extract important parts of JavaScript/TypeScript code
func extractRelevantJSCode(lines []string, maxLines int) string {
	var result []string
	
	// Add a header showing it's truncated
	result = append(result, "// NOTE: Large file - showing extracted portions only")
	result = append(result, "")
	
	// Try to find important structures (imports, classes, functions)
	inClass := false
	inFunction := false
	inImports := false
	
	importSection := []string{}
	classSections := [][]string{}
	funcSections := [][]string{}
	currentSection := []string{}
	
	for _, line := range lines {
		trimmedLine := strings.TrimSpace(line)
		
		// Track import section
		if strings.HasPrefix(trimmedLine, "import ") {
			importSection = append(importSection, line)
			inImports = true
			continue
		}
		if inImports && strings.HasPrefix(trimmedLine, "import ") {
			importSection = append(importSection, line)
			continue
		}
		inImports = false
		
		// Track class declarations
		if strings.HasPrefix(trimmedLine, "class ") {
			inClass = true
			currentSection = []string{line}
			continue
		}
		if inClass {
			currentSection = append(currentSection, line)
			if trimmedLine == "}" {
				inClass = false
				classSections = append(classSections, currentSection)
				currentSection = []string{}
			}
			continue
		}
		
		// Track function declarations (various formats)
		if strings.HasPrefix(trimmedLine, "function ") || 
		   (strings.Contains(trimmedLine, "=>") && !strings.HasPrefix(trimmedLine, "//")) ||
		   strings.HasPrefix(trimmedLine, "const ") && strings.Contains(trimmedLine, "= function") {
			inFunction = true
			currentSection = []string{line}
			continue
		}
		if inFunction {
			currentSection = append(currentSection, line)
			if trimmedLine == "}" {
				inFunction = false
				funcSections = append(funcSections, currentSection)
				currentSection = []string{}
			}
			continue
		}
	}
	
	// Add imports if found
	if len(importSection) > 0 && len(importSection) < maxLines/4 {
		result = append(result, "// Module imports")
		result = append(result, importSection...)
		result = append(result, "")
	}
	
	// Add class samples
	if len(classSections) > 0 {
		result = append(result, "// Sample class definitions")
		// Take at most 1 class
		if len(classSections) > 0 {
			result = append(result, classSections[0]...)
			result = append(result, "")
		}
		if len(classSections) > 1 {
			result = append(result, fmt.Sprintf("// ... and %d more class definitions", len(classSections)-1))
			result = append(result, "")
		}
	}
	
	// Add function samples
	if len(funcSections) > 0 {
		result = append(result, "// Sample function definitions")
		// Take at most 3 functions, preferring shorter ones
		sort.Slice(funcSections, func(i, j int) bool {
			return len(funcSections[i]) < len(funcSections[j])
		})
		
		numFuncs := 3
		if len(funcSections) < numFuncs {
			numFuncs = len(funcSections)
		}
		
		totalLines := 0
		for i := 0; i < numFuncs; i++ {
			if totalLines+len(funcSections[i]) > maxLines {
				break
			}
			result = append(result, funcSections[i]...)
			result = append(result, "")
			totalLines += len(funcSections[i]) + 1
		}
		
		if len(funcSections) > numFuncs {
			result = append(result, fmt.Sprintf("// ... and %d more functions", len(funcSections)-numFuncs))
		}
	}
	
	// If we couldn't extract structured elements, fall back to sample approach
	if len(result) < 5 {
		return extractGeneralCodeSample(lines, maxLines)
	}
	
	return strings.Join(result, "\n")
}

// extractGeneralCodeSample extracts a representative sample from any code file
func extractGeneralCodeSample(lines []string, maxLines int) string {
	var result []string
	
	// Add a header showing it's truncated
	result = append(result, "// NOTE: Large file - showing sample only")
	result = append(result, "")
	
	// Calculate sections to include
	totalLines := len(lines)
	headerLines := maxLines / 4
	middleLines := maxLines / 2
	footerLines := maxLines - headerLines - middleLines
	
	// Add header section
	result = append(result, "// Beginning of file:")
	for i := 0; i < headerLines && i < totalLines; i++ {
		result = append(result, lines[i])
	}
	result = append(result, "")
	
	// Add middle section if the file is large enough
	if totalLines > headerLines+footerLines+10 {
		middleStart := totalLines/2 - middleLines/2
		result = append(result, "// Middle portion of file:")
		for i := 0; i < middleLines && middleStart+i < totalLines; i++ {
			result = append(result, lines[middleStart+i])
		}
		result = append(result, "")
	}
	
	// Add footer section
	if totalLines > headerLines+10 {
		result = append(result, "// End of file:")
		startIdx := totalLines - footerLines
		if startIdx < 0 {
			startIdx = 0
		}
		for i := startIdx; i < totalLines; i++ {
			result = append(result, lines[i])
		}
	}
	
	return strings.Join(result, "\n")
} 