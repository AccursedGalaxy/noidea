package feedback

import (
	"log"
	"strings"
	"time"

	"github.com/AccursedGalaxy/noidea/internal/personality"
)

// CommitContext contains information about a commit
type CommitContext struct {
	Message       string
	Timestamp     time.Time
	Diff          string                 // Optional
	CommitHistory []string               // Recent commit messages
	CommitStats   map[string]interface{} // Stats about recent commits
}

// FeedbackEngine defines the interface for generating commit feedback
type FeedbackEngine interface {
	// Generate feedback based on commit context
	GenerateFeedback(context CommitContext) (string, error)

	// Generate insights for a weekly summary
	GenerateSummaryFeedback(context CommitContext) (string, error)

	// Generate commit message suggestions based on staged changes and history
	GenerateCommitSuggestion(context CommitContext) (string, error)
}

// EngineName returns a string identifier for an engine type
type EngineName string

const (
	// Local feedback engine (no LLM)
	EngineLocal EngineName = "local"
	// xAI feedback engine
	EngineXAI EngineName = "xai"
	// OpenAI feedback engine
	EngineOpenAI EngineName = "openai"
	// DeepSeek feedback engine
	EngineDeepSeek EngineName = "deepseek"
)

// NewFeedbackEngine creates a new feedback engine based on the provided configuration
func NewFeedbackEngine(provider string, model string, apiKey string, personalityName string, personalityFile string, debug bool) FeedbackEngine {
	// No API key means we have to use the local engine
	if apiKey == "" {
		log.Println("No API key provided, falling back to local feedback engine")
		return NewLocalFeedbackEngine()
	}

	// Handle different providers
	switch strings.ToLower(provider) {
	case "xai", "openai", "deepseek":
		// Use the unified engine with the appropriate provider
		return NewUnifiedFeedbackEngine(provider, model, apiKey, personalityName, personalityFile, debug)
	default:
		// If provider not recognized, fallback to local
		log.Printf("Unknown provider %s, falling back to local feedback engine", provider)
		return NewLocalFeedbackEngine()
	}
}

// NewFeedbackEngineWithCustomPersonality creates a feedback engine using a custom personality configuration
func NewFeedbackEngineWithCustomPersonality(provider string, model string, apiKey string, customPersonality personality.Personality, debug bool) FeedbackEngine {
	// No API key means we have to use the local engine
	if apiKey == "" {
		log.Println("No API key provided, falling back to local feedback engine")
		return NewLocalFeedbackEngine()
	}

	// Handle different providers
	switch strings.ToLower(provider) {
	case "xai", "openai", "deepseek":
		// Use the unified engine with the custom personality
		return NewUnifiedFeedbackEngineWithCustomPersonality(provider, model, apiKey, customPersonality, debug)
	default:
		// If provider not recognized, fallback to local
		log.Printf("Unknown provider %s, falling back to local feedback engine", provider)
		return NewLocalFeedbackEngine()
	}
}
