package feedback

import (
	"time"
)

// CommitContext contains information about a commit
type CommitContext struct {
	Message   string
	Timestamp time.Time
	Diff      string // Optional
}

// FeedbackEngine defines the interface for generating commit feedback
type FeedbackEngine interface {
	// Generate feedback based on commit context
	GenerateFeedback(context CommitContext) (string, error)
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
func NewFeedbackEngine(provider string, model string, apiKey string) FeedbackEngine {
	// If we have a valid API key, use the unified engine
	if apiKey != "" {
		return NewUnifiedFeedbackEngine(provider, model, apiKey)
	}

	// Fallback to local feedback engine if no API key is provided
	return NewLocalFeedbackEngine()
} 