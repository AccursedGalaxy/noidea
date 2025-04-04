package github

import (
	"context"
	"fmt"
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
	ghIssue, _, err := client.Issues.Create(ctx, owner, repo, req)
	if err != nil {
		return nil, fmt.Errorf("failed to create issue: %w", err)
	}
	
	// Convert to our format
	issue := convertGitHubIssue(ghIssue)
	issue.Repository = fmt.Sprintf("%s/%s", owner, repo)
	
	return &issue, nil
}

// CloseIssue closes an issue
func (s *IssueService) CloseIssue(owner, repo string, number int) error {
	// Get authenticated client
	client, err := s.auth.Client()
	if err != nil {
		return err
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