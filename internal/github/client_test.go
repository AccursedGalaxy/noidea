package github

import (
	"strings"
	"testing"
	"time"
)

// TestNewClientWithoutAuth
func TestNewClientWithoutAuth(t *testing.T) {
	client := NewClientWithoutAuth()
	if client == nil {
		t.Fatal("Expected non-nil client")
	}
	if client.token != "" {
		t.Errorf("Expected empty token, got '%s'", client.token)
	}
	if client.baseURL != "https://api.github.com" {
		t.Errorf("Expected baseURL 'https://api.github.com', got %s", client.baseURL)
	}
	if client.httpClient.Timeout != 10*time.Second {
		t.Errorf("Expected timeout 10s, got %v", client.httpClient.Timeout)
	}
}

// TestExtractRepoInfo_HTTPS
func TestExtractRepoInfo_HTTPS(t *testing.T) {
	owner, repo, err := ExtractRepoInfo("https://github.com/testowner/testrepo.git")
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}
	if owner != "testowner" {
		t.Errorf("Expected owner 'testowner', got '%s'", owner)
	}
	if repo != "testrepo" {
		t.Errorf("Expected repo 'testrepo', got '%s'", repo)
	}
}

// TestExtractRepoInfo_SSH
func TestExtractRepoInfo_SSH(t *testing.T) {
	owner, repo, err := ExtractRepoInfo("git@github.com:testowner/testrepo.git")
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}
	if owner != "testowner" {
		t.Errorf("Expected owner 'testowner', got '%s'", owner)
	}
	if repo != "testrepo" {
		t.Errorf("Expected repo 'testrepo', got '%s'", repo)
	}
}

// TestExtractRepoInfo_Empty (skipped, requires exec mock)
func TestExtractRepoInfo_Empty(t *testing.T) {
	t.Skip("Requires git repo setup or exec mock")
	// owner, repo, err := ExtractRepoInfo("")
	// if err != nil {
	// 	t.Skipf("Skipping due to git error: %v", err)
	// }
	// // Assertions based on test repo
}

// TestExtractRepoInfo_Invalid
func TestExtractRepoInfo_Invalid(t *testing.T) {
	_, _, err := ExtractRepoInfo("invalid-url")
	if err == nil {
		t.Fatal("Expected error")
	}
	if !strings.Contains(err.Error(), "could not parse") {
		t.Errorf("Expected parse error, got %v", err)
	}
}

// TestIsAuthenticated (skipped, requires HTTP mock)
func TestIsAuthenticated(t *testing.T) {
	t.Skip("Requires HTTP mock")
}

// TestGetLatestRelease (skipped, requires HTTP mock)
func TestGetLatestRelease(t *testing.T) {
	// client := NewClientWithoutAuth()
	t.Skip("Requires HTTP mock")
}

// TestDoRequest (skipped, requires HTTP mock)
func TestDoRequest(t *testing.T) {
	// client := &Client{token: "test"}
	// req, _ := http.NewRequest("GET", "/test", nil)
	t.Skip("Requires HTTP mock for client.httpClient.Do")
}
