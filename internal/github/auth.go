// Package github provides integration with GitHub API for issue tracking and project management
package github

import (
	"context"
	"errors"
	"fmt"
	"os"
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
)

var (
	// ErrNoToken is returned when no GitHub token is available
	ErrNoToken = errors.New("no GitHub token available")
)

// Authenticator handles GitHub authentication
type Authenticator struct {
	token string
	client *github.Client
}

// NewAuthenticator creates a new GitHub authenticator
func NewAuthenticator() *Authenticator {
	return &Authenticator{}
}

// GetToken retrieves the GitHub token from secure storage or environment
func (a *Authenticator) GetToken() (string, error) {
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
	
	// Update cached token
	a.token = token
	return nil
}

// Client returns an authenticated GitHub client
func (a *Authenticator) Client() (*github.Client, error) {
	// Return cached client if available
	if a.client != nil {
		return a.client, nil
	}
	
	// Get token
	token, err := a.GetToken()
	if err != nil {
		return nil, err
	}
	
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