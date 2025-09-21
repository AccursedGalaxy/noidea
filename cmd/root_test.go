package cmd

import (
	"bytes"
	"os"
	"strings"
	"testing"
)

// TestRootCommand tests the root command execution
func TestRootCommand(t *testing.T) {
	// Save and restore original args
	oldArgs := os.Args
	defer func() { os.Args = oldArgs }()

	// Test with no arguments (should print help)
	os.Args = []string{"noidea"}

	// Capture stdout
	oldStdout := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	// Execute the command
	err := rootCmd.Execute()

	// Restore stdout
	w.Close()
	os.Stdout = oldStdout

	// Check for errors
	if err != nil {
		t.Errorf("rootCmd.Execute failed: %v", err)
	}

	// Read captured output
	var buf bytes.Buffer
	buf.ReadFrom(r)
	output := buf.String()

	// Verify that help text is displayed
	if !strings.Contains(output, "Usage:") || !strings.Contains(output, "Available Commands:") {
		t.Errorf("Expected help text, got: %s", output)
	}
}

// TestVersionFlag tests the version flag functionality
func TestVersionFlag(t *testing.T) {
	// Save and restore original args
	oldArgs := os.Args
	defer func() { os.Args = oldArgs }()

	// Test with version flag
	os.Args = []string{"noidea", "--version"}

	// Reset version flag
	versionFlag = false

	// Capture stdout
	oldStdout := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	// Execute the command
	err := rootCmd.Execute()

	// Restore stdout
	w.Close()
	os.Stdout = oldStdout

	// Check for errors
	if err != nil {
		t.Errorf("rootCmd.Execute with --version failed: %v", err)
	}

	// Read captured output
	var buf bytes.Buffer
	buf.ReadFrom(r)
	output := buf.String()

	// Verify that version info is displayed
	if !strings.Contains(output, "noidea version") {
		t.Errorf("Expected version info, got: %s", output)
	}
}

// TestEnvFilesLoading tests environment file loading
func TestEnvFilesLoading(t *testing.T) {
	// Create a temporary env file
	tmpFile, err := os.CreateTemp(".", "noidea-test-env")
	if err != nil {
		t.Fatalf("Failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Write test environment variables
	envContent := `TEST_VAR1=value1
TEST_VAR2="value 2"
# This is a comment
TEST_VAR3='value 3'

`
	if _, err := tmpFile.WriteString(envContent); err != nil {
		t.Fatalf("Failed to write to temp file: %v", err)
	}
	tmpFile.Close()

	// Save the old values to restore later
	oldEnv := make(map[string]string)
	for _, key := range []string{"TEST_VAR1", "TEST_VAR2", "TEST_VAR3"} {
		oldEnv[key] = os.Getenv(key)
		os.Unsetenv(key)
	}
	defer func() {
		for key, value := range oldEnv {
			if value == "" {
				os.Unsetenv(key)
			} else {
				os.Setenv(key, value)
			}
		}
	}()

	// Rename temp file to .env in the current directory
	// (Save the old one if it exists)
	if _, err := os.Stat(".env"); err == nil {
		if err := os.Rename(".env", ".env.backup"); err != nil {
			t.Fatalf("Failed to backup .env file: %v", err)
		}
		defer os.Rename(".env.backup", ".env")
	}
	if err := os.Rename(tmpFile.Name(), ".env"); err != nil {
		t.Fatalf("Failed to move temp file to .env: %v", err)
	}
	defer os.Remove(".env")

	// Call loadEnvFiles
	loadEnvFiles()

	// Check if environment variables were loaded
	if os.Getenv("TEST_VAR1") != "value1" {
		t.Errorf("TEST_VAR1 not loaded correctly, got: %s", os.Getenv("TEST_VAR1"))
	}

	if os.Getenv("TEST_VAR2") != "value 2" {
		t.Errorf("TEST_VAR2 not loaded correctly, got: %s", os.Getenv("TEST_VAR2"))
	}

	if os.Getenv("TEST_VAR3") != "value 3" {
		t.Errorf("TEST_VAR3 not loaded correctly, got: %s", os.Getenv("TEST_VAR3"))
	}
}

// TestValidateAPIKey tests API key validation
func TestValidateAPIKey(t *testing.T) {
	testCases := []struct {
		name       string
		provider   string
		shouldFail bool
	}{
		{"Valid provider: xai", "xai", false},
		{"Valid provider: openai", "openai", false},
		{"Valid provider: deepseek", "deepseek", false},
		{"Unknown provider", "unknown", true},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := validateAPIKey(tc.provider, "dummy-key")

			if tc.shouldFail && err == nil {
				t.Errorf("Expected validation to fail for provider %s, but it succeeded", tc.provider)
			}

			if !tc.shouldFail && err != nil {
				t.Errorf("Expected validation to succeed for provider %s, but got error: %v", tc.provider, err)
			}
		})
	}
}
