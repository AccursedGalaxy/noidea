package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	// Verify default values are set correctly
	if !cfg.LLM.Enabled == false {
		t.Errorf("Expected LLM.Enabled to be false, got %v", cfg.LLM.Enabled)
	}

	if cfg.LLM.Provider != "xai" {
		t.Errorf("Expected default provider to be 'xai', got %s", cfg.LLM.Provider)
	}

	if cfg.LLM.Model != "grok-4-fast-reasoning" {
		t.Errorf("Expected default model to be 'grok-4-fast-reasoning', got %s", cfg.LLM.Model)
	}

	if cfg.LLM.Temperature != 0.7 {
		t.Errorf("Expected default temperature to be 0.7, got %f", cfg.LLM.Temperature)
	}

	if cfg.Moai.UseLint != false {
		t.Errorf("Expected Moai.UseLint to be false, got %v", cfg.Moai.UseLint)
	}

	if cfg.Moai.FacesMode != "random" {
		t.Errorf("Expected Moai.FacesMode to be 'random', got %s", cfg.Moai.FacesMode)
	}

	if cfg.Moai.Personality != "professional_sass" {
		t.Errorf("Expected Moai.Personality to be 'professional_sass', got %s", cfg.Moai.Personality)
	}
}

func TestValidateConfig(t *testing.T) {
	// Create a temporary personalities file
	tempDir, err := os.MkdirTemp("", "noidea-test")
	if err != nil {
		t.Fatalf("Failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir)

	// Create fake personalities file
	personalityFile := filepath.Join(tempDir, "personalities.json")
	if err := os.WriteFile(personalityFile, []byte("{}"), 0644); err != nil {
		t.Fatalf("Failed to create personality file: %v", err)
	}

	// Test a valid config
	validConfig := DefaultConfig()
	validConfig.LLM.Enabled = true
	validConfig.LLM.APIKey = "test-api-key"
	validConfig.Moai.PersonalityFile = personalityFile

	issues := ValidateConfig(validConfig)
	if len(issues) > 0 {
		t.Errorf("Expected no issues with valid config, got %v", issues)
	}

	// Test invalid provider
	invalidProvider := DefaultConfig()
	invalidProvider.LLM.Enabled = true
	invalidProvider.LLM.Provider = "invalid-provider"
	invalidProvider.LLM.APIKey = "test-api-key"
	invalidProvider.Moai.PersonalityFile = personalityFile

	issues = ValidateConfig(invalidProvider)
	if len(issues) == 0 {
		t.Errorf("Expected issues with invalid provider, got none")
	}

	// Test missing API key
	missingAPIKey := DefaultConfig()
	missingAPIKey.LLM.Enabled = true
	missingAPIKey.LLM.APIKey = ""
	missingAPIKey.Moai.PersonalityFile = personalityFile

	issues = ValidateConfig(missingAPIKey)
	if len(issues) == 0 {
		t.Errorf("Expected issues with missing API key, got none")
	}

	// Test invalid temperature
	invalidTemp := DefaultConfig()
	invalidTemp.LLM.Enabled = true
	invalidTemp.LLM.APIKey = "test-api-key"
	invalidTemp.LLM.Temperature = 1.5 // Outside valid range
	invalidTemp.Moai.PersonalityFile = personalityFile

	issues = ValidateConfig(invalidTemp)
	if len(issues) == 0 {
		t.Errorf("Expected issues with invalid temperature, got none")
	}

	// Test invalid faces mode
	invalidFacesMode := DefaultConfig()
	invalidFacesMode.Moai.FacesMode = "invalid-mode"
	invalidFacesMode.Moai.PersonalityFile = personalityFile

	issues = ValidateConfig(invalidFacesMode)
	if len(issues) == 0 {
		t.Errorf("Expected issues with invalid faces mode, got none")
	}
}

func TestParseFloat(t *testing.T) {
	tests := []struct {
		input    string
		defValue float64
		expected float64
	}{
		{"0.5", 1.0, 0.5},
		{"1.0", 0.5, 1.0},
		{"invalid", 0.7, 0.7}, // Should return default value for invalid input
		{"", 0.3, 0.3},        // Should return default value for empty string
	}

	for _, test := range tests {
		result := ParseFloat(test.input, test.defValue)
		if result != test.expected {
			t.Errorf("ParseFloat(%s, %f) = %f, expected %f",
				test.input, test.defValue, result, test.expected)
		}
	}
}

func TestApplyEnvironmentOverrides(t *testing.T) {
	// Save original environment and restore at end
	origEnv := os.Environ()
	defer func() {
		os.Clearenv()
		for _, e := range origEnv {
			pair := filepath.SplitList(e)
			if len(pair) == 2 {
				os.Setenv(pair[0], pair[1])
			}
		}
	}()

	// Clear environment for test
	os.Clearenv()

	// Test overriding LLM settings
	os.Setenv("NOIDEA_LLM_ENABLED", "true")
	os.Setenv("NOIDEA_LLM_PROVIDER", "openai")
	os.Setenv("NOIDEA_API_KEY", "test-api-key")
	os.Setenv("NOIDEA_MODEL", "gpt-4")
	os.Setenv("NOIDEA_TEMPERATURE", "0.8")

	// Test overriding Moai settings
	os.Setenv("NOIDEA_USE_LINT", "true")
	os.Setenv("NOIDEA_FACES_MODE", "mood")
	os.Setenv("NOIDEA_PERSONALITY", "sarcastic")
	os.Setenv("NOIDEA_PERSONALITY_FILE", "test-file.json")

	cfg := DefaultConfig()
	cfg = applyEnvironmentOverrides(cfg)

	// Verify LLM overrides
	if !cfg.LLM.Enabled {
		t.Error("Expected LLM.Enabled to be true after environment override")
	}
	if cfg.LLM.Provider != "openai" {
		t.Errorf("Expected LLM.Provider to be 'openai', got '%s'", cfg.LLM.Provider)
	}
	if cfg.LLM.APIKey != "test-api-key" {
		t.Errorf("Expected LLM.APIKey to be 'test-api-key', got '%s'", cfg.LLM.APIKey)
	}
	if cfg.LLM.Model != "gpt-4" {
		t.Errorf("Expected LLM.Model to be 'gpt-4', got '%s'", cfg.LLM.Model)
	}
	if cfg.LLM.Temperature != 0.8 {
		t.Errorf("Expected LLM.Temperature to be 0.8, got %f", cfg.LLM.Temperature)
	}

	// Verify Moai overrides
	if !cfg.Moai.UseLint {
		t.Error("Expected Moai.UseLint to be true after environment override")
	}
	if cfg.Moai.FacesMode != "mood" {
		t.Errorf("Expected Moai.FacesMode to be 'mood', got '%s'", cfg.Moai.FacesMode)
	}
	if cfg.Moai.Personality != "sarcastic" {
		t.Errorf("Expected Moai.Personality to be 'sarcastic', got '%s'", cfg.Moai.Personality)
	}
	if cfg.Moai.PersonalityFile != "test-file.json" {
		t.Errorf("Expected Moai.PersonalityFile to be 'test-file.json', got '%s'", cfg.Moai.PersonalityFile)
	}
}
