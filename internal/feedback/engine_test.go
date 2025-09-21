package feedback

import (
	"testing"

	"github.com/AccursedGalaxy/noidea/internal/personality"
)

// Assuming LocalFeedbackEngine and UnifiedFeedbackEngine are exported types from local.go and unified.go
// If not, adjust type assertions accordingly

func TestNewFeedbackEngine_NoAPIKey_ReturnsLocal(t *testing.T) {
	engine := NewFeedbackEngine("xai", "mixtral-8x7b-32768", "", "default", "", false)
	if engine == nil {
		t.Fatal("Expected non-nil engine")
	}

	// Type assert to LocalFeedbackEngine
	if _, ok := engine.(*LocalFeedbackEngine); !ok {
		t.Errorf("Expected LocalFeedbackEngine, got %T", engine)
	}
}

func TestNewFeedbackEngine_ValidProvider_ReturnsUnified(t *testing.T) {
	tests := []struct {
		provider string
	}{
		{"xai"},
		{"openai"},
		{"deepseek"},
	}

	for _, tt := range tests {
		t.Run(tt.provider, func(t *testing.T) {
			engine := NewFeedbackEngine(tt.provider, "gpt-4", "dummy-key", "default", "", false)
			if engine == nil {
				t.Fatal("Expected non-nil engine")
			}

			// Type assert to UnifiedFeedbackEngine
			if _, ok := engine.(*UnifiedFeedbackEngine); !ok {
				t.Errorf("Expected UnifiedFeedbackEngine for %s, got %T", tt.provider, engine)
			}
		})
	}
}

func TestNewFeedbackEngine_InvalidProvider_ReturnsLocal(t *testing.T) {
	engine := NewFeedbackEngine("invalid", "model", "dummy-key", "default", "", false)
	if engine == nil {
		t.Fatal("Expected non-nil engine")
	}

	if _, ok := engine.(*LocalFeedbackEngine); !ok {
		t.Errorf("Expected LocalFeedbackEngine, got %T", engine)
	}
}

func TestNewFeedbackEngineWithCustomPersonality_NoAPIKey_ReturnsLocal(t *testing.T) {
	customPersonality := personality.Personality{Name: "test"}
	engine := NewFeedbackEngineWithCustomPersonality("xai", "mixtral-8x7b-32768", "", customPersonality, false)
	if engine == nil {
		t.Fatal("Expected non-nil engine")
	}

	if _, ok := engine.(*LocalFeedbackEngine); !ok {
		t.Errorf("Expected LocalFeedbackEngine, got %T", engine)
	}
}

func TestNewFeedbackEngineWithCustomPersonality_ValidProvider_ReturnsUnified(t *testing.T) {
	tests := []struct {
		provider string
	}{
		{"xai"},
		{"openai"},
		{"deepseek"},
	}

	for _, tt := range tests {
		t.Run(tt.provider, func(t *testing.T) {
			customPersonality := personality.Personality{Name: "test"}
			engine := NewFeedbackEngineWithCustomPersonality(tt.provider, "gpt-4", "dummy-key", customPersonality, false)
			if engine == nil {
				t.Fatal("Expected non-nil engine")
			}

			if _, ok := engine.(*UnifiedFeedbackEngine); !ok {
				t.Errorf("Expected UnifiedFeedbackEngine for %s, got %T", tt.provider, engine)
			}
		})
	}
}

func TestNewFeedbackEngineWithCustomPersonality_InvalidProvider_ReturnsLocal(t *testing.T) {
	customPersonality := personality.Personality{Name: "test"}
	engine := NewFeedbackEngineWithCustomPersonality("invalid", "model", "dummy-key", customPersonality, false)
	if engine == nil {
		t.Fatal("Expected non-nil engine")
	}

	if _, ok := engine.(*LocalFeedbackEngine); !ok {
		t.Errorf("Expected LocalFeedbackEngine, got %T", engine)
	}
}
