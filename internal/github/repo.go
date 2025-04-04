package github

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

var (
	// ErrNotGitRepo is returned when the current directory is not a Git repository
	ErrNotGitRepo = errors.New("not a Git repository")
	
	// ErrNoRemoteRepo is returned when the repository has no GitHub remote
	ErrNoRemoteRepo = errors.New("no GitHub remote repository found")
)

// RepoInfo contains information about a GitHub repository
type RepoInfo struct {
	Owner string
	Name  string
	URL   string
}

// GetCurrentRepo gets information about the current repository
func GetCurrentRepo() (*RepoInfo, error) {
	// Check if we're in a Git repository
	if _, err := os.Stat(".git"); err != nil {
		// Try to execute git rev-parse to check if we're in a git repo
		cmd := exec.Command("git", "rev-parse", "--is-inside-work-tree")
		if err := cmd.Run(); err != nil {
			return nil, ErrNotGitRepo
		}
	}
	
	// Get the remote URL
	cmd := exec.Command("git", "config", "--get", "remote.origin.url")
	output, err := cmd.Output()
	if err != nil {
		return nil, ErrNoRemoteRepo
	}
	
	// Parse the remote URL to extract owner and repo name
	remoteURL := strings.TrimSpace(string(output))
	owner, name, err := parseGitHubURL(remoteURL)
	if err != nil {
		return nil, err
	}
	
	return &RepoInfo{
		Owner: owner,
		Name:  name,
		URL:   remoteURL,
	}, nil
}

// parseGitHubURL extracts owner and repo name from various GitHub URL formats
func parseGitHubURL(url string) (string, string, error) {
	// Handle SSH style: git@github.com:owner/repo.git
	if strings.HasPrefix(url, "git@github.com:") {
		parts := strings.TrimPrefix(url, "git@github.com:")
		return parsePath(parts)
	}
	
	// Handle HTTPS style: https://github.com/owner/repo.git
	if strings.HasPrefix(url, "https://github.com/") {
		parts := strings.TrimPrefix(url, "https://github.com/")
		return parsePath(parts)
	}
	
	// Handle HTTP style: http://github.com/owner/repo.git
	if strings.HasPrefix(url, "http://github.com/") {
		parts := strings.TrimPrefix(url, "http://github.com/")
		return parsePath(parts)
	}
	
	// Handle GH CLI style: github.com/owner/repo
	if strings.HasPrefix(url, "github.com/") {
		parts := strings.TrimPrefix(url, "github.com/")
		return parsePath(parts)
	}
	
	return "", "", fmt.Errorf("not a GitHub repository URL: %s", url)
}

// parsePath extracts owner and repo from a path string
func parsePath(path string) (string, string, error) {
	// Remove .git suffix if present
	path = strings.TrimSuffix(path, ".git")
	
	// Split by slash
	parts := strings.Split(path, "/")
	if len(parts) < 2 {
		return "", "", fmt.Errorf("invalid GitHub repository path: %s", path)
	}
	
	owner := parts[0]
	repo := parts[1]
	
	return owner, repo, nil
}

// GetRepositoryDetails fetches additional details about a repository
func GetRepositoryDetails(auth *Authenticator, owner, repo string) (map[string]interface{}, error) {
	// Get authenticated client
	client, err := auth.Client()
	if err != nil {
		return nil, err
	}
	
	// Call GitHub API
	ctx := context.Background()
	repository, _, err := client.Repositories.Get(ctx, owner, repo)
	if err != nil {
		return nil, fmt.Errorf("failed to get repository details: %w", err)
	}
	
	// Extract relevant details
	details := make(map[string]interface{})
	
	details["name"] = *repository.Name
	details["full_name"] = *repository.FullName
	details["description"] = ""
	if repository.Description != nil {
		details["description"] = *repository.Description
	}
	
	details["url"] = *repository.HTMLURL
	details["stars"] = *repository.StargazersCount
	details["forks"] = *repository.ForksCount
	details["open_issues"] = *repository.OpenIssuesCount
	details["default_branch"] = *repository.DefaultBranch
	details["is_private"] = *repository.Private
	
	if repository.License != nil && repository.License.Name != nil {
		details["license"] = *repository.License.Name
	} else {
		details["license"] = "None"
	}
	
	return details, nil
} 