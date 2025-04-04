// Package github provides integration with GitHub API for issue tracking and project management
package github

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/AccursedGalaxy/noidea/internal/secure"
	"github.com/google/go-github/v54/github"
	"golang.org/x/oauth2"
)

const (
	// ServiceName for storing GitHub tokens
	ServiceName = "noidea-github-token"
	
	// EnvGitHubToken is the environment variable name for GitHub token
	EnvGitHubToken = "GITHUB_TOKEN"
	
	// SSHKeyPathService for storing SSH key path
	SSHKeyPathService = "noidea-github-sshkey"
)

var (
	// ErrNoToken is returned when no GitHub token is available
	ErrNoToken = errors.New("no GitHub token available")
	
	// ErrNoSSHKey is returned when no SSH key is available
	ErrNoSSHKey = errors.New("no SSH key available")
)

// Authenticator handles GitHub authentication
type Authenticator struct {
	token    string
	client   *github.Client
	sshPath  string
	username string
	useSSH   bool
}

// NewAuthenticator creates a new GitHub authenticator
func NewAuthenticator() *Authenticator {
	return &Authenticator{}
}

// GetToken retrieves the GitHub token from secure storage or environment
func (a *Authenticator) GetToken() (string, error) {
	// Check if we're using SSH-based authentication
	if a.useSSH || a.sshPath != "" {
		return "", ErrNoToken
	}
	
	// Return cached token if available
	if a.token != "" {
		return a.token, nil
	}
	
	// Try to get token from environment
	token := os.Getenv(EnvGitHubToken)
	if token != "" {
		a.token = token
		return token, nil
	}
	
	// Try to get token from secure storage
	token, err := secure.GetAPIKey(ServiceName)
	if err == nil && token != "" {
		a.token = token
		return token, nil
	}
	
	return "", ErrNoToken
}

// SetToken stores a GitHub token in secure storage
func (a *Authenticator) SetToken(token string) error {
	// Clean the token (remove whitespace)
	token = strings.TrimSpace(token)
	
	// Validate token format (basic check)
	if !strings.HasPrefix(token, "ghp_") && !strings.HasPrefix(token, "github_pat_") {
		return fmt.Errorf("invalid GitHub token format")
	}
	
	// Store token in secure storage
	if err := secure.StoreAPIKey(ServiceName, token); err != nil {
		return fmt.Errorf("failed to store GitHub token: %w", err)
	}
	
	// Clear any SSH settings since we're now using token
	a.useSSH = false
	a.sshPath = ""
	if err := secure.DeleteAPIKey(SSHKeyPathService); err != nil {
		// Non-fatal error, just log it
		fmt.Fprintf(os.Stderr, "Warning: Could not clear SSH key path: %v\n", err)
	}
	
	// Update cached token
	a.token = token
	return nil
}

// SetSSHKeyPath configures SSH-based authentication
func (a *Authenticator) SetSSHKeyPath(keyPath string) error {
	// Verify the key exists
	if _, err := os.Stat(keyPath); err != nil {
		return fmt.Errorf("SSH key not found at %s: %w", keyPath, err)
	}
	
	// Store the path securely
	if err := secure.StoreAPIKey(SSHKeyPathService, keyPath); err != nil {
		return fmt.Errorf("failed to store SSH key path: %w", err)
	}
	
	// Clear any token to prevent confusion
	a.token = ""
	if err := secure.DeleteAPIKey(ServiceName); err != nil {
		// Non-fatal error, just log it
		fmt.Fprintf(os.Stderr, "Warning: Could not clear token: %v\n", err)
	}
	
	// Configure for SSH
	a.sshPath = keyPath
	a.useSSH = true
	
	// Try to determine username
	username, err := a.getGitHubSSHUsername(keyPath)
	if err == nil {
		a.username = username
	}
	
	return nil
}

// getGitHubSSHUsername attempts to get the GitHub username from SSH
func (a *Authenticator) getGitHubSSHUsername(keyPath string) (string, error) {
	// Use SSH to connect to GitHub and extract username
	cmd := exec.Command("ssh", "-T", "-o", "BatchMode=yes", "-i", keyPath, "git@github.com")
	output, _ := cmd.CombinedOutput() // Ignore error as GitHub SSH always returns exit code 1
	outputStr := string(output)
	
	// GitHub SSH test always returns error code 1, but we're looking for the greeting
	if !strings.Contains(outputStr, "Hi ") {
		return "", fmt.Errorf("failed to authenticate with GitHub SSH: %s", outputStr)
	}
	
	// Extract username from "Hi username!" pattern
	parts := strings.Split(outputStr, "Hi ")
	if len(parts) < 2 {
		return "", fmt.Errorf("could not find username in SSH response")
	}
	
	usernamePart := parts[1]
	endIdx := strings.Index(usernamePart, "!")
	if endIdx < 0 {
		return "", fmt.Errorf("invalid SSH response format")
	}
	
	username := usernamePart[:endIdx]
	return strings.TrimSpace(username), nil
}

// GetSSHKeyPath retrieves the stored SSH key path
func (a *Authenticator) GetSSHKeyPath() (string, error) {
	// Return cached path if available
	if a.sshPath != "" {
		return a.sshPath, nil
	}
	
	// Try to get path from secure storage
	path, err := secure.GetAPIKey(SSHKeyPathService)
	if err == nil && path != "" {
		a.sshPath = path
		a.useSSH = true
		return path, nil
	}
	
	return "", ErrNoSSHKey
}

// Client returns an authenticated GitHub client
func (a *Authenticator) Client() (*github.Client, error) {
	// Return cached client if available
	if a.client != nil {
		return a.client, nil
	}
	
	// First try token-based authentication (required for GitHub API)
	token, tokenErr := a.GetToken()
	if tokenErr == nil && token != "" {
		// Create OAuth2 token source
		ts := oauth2.StaticTokenSource(
			&oauth2.Token{AccessToken: token},
		)
		tc := oauth2.NewClient(context.Background(), ts)
		
		// Create GitHub client
		client := github.NewClient(tc)
		
		// Cache client
		a.client = client
		
		return client, nil
	}
	
	// Check if we're using SSH - but warn that it's limited for API operations
	sshKeyPath, _ := secure.GetAPIKey(SSHKeyPathService)
	if a.useSSH || a.sshPath != "" || sshKeyPath != "" {
		// For SSH, we use unauthenticated client - but this has limited API access
		// The user will need a token for full API access
		client := github.NewClient(nil)
		a.client = client
		a.useSSH = true
		
		// Return with a clear warning in the error that indicates the limitation
		return client, fmt.Errorf("using SSH authentication, but GitHub API operations require a token: %w", ErrNoToken)
	}
	
	// No authentication method available
	return nil, ErrNoToken
}

// ValidateToken checks if the GitHub token is valid
func (a *Authenticator) ValidateToken(token string) (bool, error) {
	// Create context
	ctx := context.Background()
	
	// Create temporary client with this token
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: token},
	)
	tc := oauth2.NewClient(ctx, ts)
	client := github.NewClient(tc)
	
	// Try to get the authenticated user
	_, _, err := client.Users.Get(ctx, "")
	if err != nil {
		return false, err
	}
	
	return true, nil
}

// GetAuthenticatedUser returns the authenticated user
func (a *Authenticator) GetAuthenticatedUser() (string, error) {
	// If we already have the username cached from SSH, return it
	if a.useSSH && a.username != "" {
		return a.username, nil
	}
	
	// If using SSH but no username cached, try to get it
	if a.useSSH || a.sshPath != "" {
		// Get SSH key path
		keyPath, err := a.GetSSHKeyPath()
		if err != nil {
			return "", err
		}
		
		// Try to get username via SSH
		username, err := a.getGitHubSSHUsername(keyPath)
		if err == nil {
			a.username = username
			return username, nil
		}
		
		// If failed to get username via SSH but we know we're using SSH,
		// return a placeholder until we can determine the actual username
		return "git user", nil
	}
	
	// Get client
	client, err := a.Client()
	if err != nil {
		return "", err
	}
	
	// Get authenticated user
	ctx := context.Background()
	user, _, err := client.Users.Get(ctx, "")
	if err != nil {
		return "", err
	}
	
	return *user.Login, nil
}

// DeleteToken removes the GitHub token from secure storage
func (a *Authenticator) DeleteToken() error {
	if err := secure.DeleteAPIKey(ServiceName); err != nil {
		return fmt.Errorf("failed to delete GitHub token: %w", err)
	}
	
	// Clear cached token and client
	a.token = ""
	a.client = nil
	
	return nil
}

// DeleteSSHKey removes the SSH key path from secure storage
func (a *Authenticator) DeleteSSHKey() error {
	if err := secure.DeleteAPIKey(SSHKeyPathService); err != nil {
		return fmt.Errorf("failed to delete SSH key path: %w", err)
	}
	
	// Clear cached SSH info and client
	a.sshPath = ""
	a.useSSH = false
	a.client = nil
	
	return nil
}

// UseSSH returns whether SSH authentication is being used
func (a *Authenticator) UseSSH() bool {
	// If we already know we're using SSH
	if a.useSSH {
		return true
	}
	
	// Try to get SSH key path to confirm we're using SSH
	_, err := a.GetSSHKeyPath()
	a.useSSH = (err == nil)
	
	return a.useSSH
} 