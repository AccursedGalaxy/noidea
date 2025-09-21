package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// TestCase defines a simulation test case
type TestCase struct {
	Name        string   `json:"name"`
	Command     string   `json:"command"`
	Args        []string `json:"args"`
	Description string   `json:"description"`
	Repetitions int      `json:"repetitions"`
}

// TestSuite defines a set of test cases
type TestSuite struct {
	Name      string     `json:"name"`
	OutputDir string     `json:"output_dir"`
	TestCases []TestCase `json:"test_cases"`
}

// LoadTestSuite loads a test suite from a JSON file
func LoadTestSuite(filename string) (TestSuite, error) {
	var suite TestSuite
	data, err := os.ReadFile(filename)
	if err != nil {
		return suite, err
	}

	err = json.Unmarshal(data, &suite)
	return suite, err
}

// SaveTestSuite saves a test suite to a JSON file
func SaveTestSuite(suite TestSuite, filename string) error {
	data, err := json.MarshalIndent(suite, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, data, 0644)
}

// RunTestSuite runs all test cases in a test suite and captures output
func RunTestSuite(suite TestSuite) error {
	// Create output directory
	outputDir := suite.OutputDir
	if outputDir == "" {
		outputDir = "test_results"
	}

	os.MkdirAll(outputDir, 0755)

	// Save summary of test suite
	summaryFile := filepath.Join(outputDir, "summary.txt")
	summary, err := os.Create(summaryFile)
	if err != nil {
		return err
	}
	defer summary.Close()

	// Create debug log file
	debugLogFile := filepath.Join(outputDir, "debug.log")
	debugLog, err := os.Create(debugLogFile)
	if err != nil {
		fmt.Printf("Warning: Failed to create debug log: %v\n", err)
	} else {
		defer debugLog.Close()
	}

	// Helper function to log debug messages
	logDebug := func(format string, args ...interface{}) {
		msg := fmt.Sprintf(format, args...)
		fmt.Println(msg) // Print to console

		if debugLog != nil {
			timestamp := time.Now().Format("2006-01-02 15:04:05")
			fmt.Fprintf(debugLog, "[%s] %s\n", timestamp, msg)
		}
	}

	logDebug("Starting test suite: %s", suite.Name)
	fmt.Fprintf(summary, "# Test Suite: %s\n", suite.Name)
	fmt.Fprintf(summary, "Run at: %s\n\n", time.Now().Format(time.RFC3339))

	// Try to load .env file from project root
	LoadEnvFile("../.env")

	// Check if we have an API key, if not use a mock one
	apiKey := os.Getenv("XAI_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
	}
	if apiKey == "" {
		apiKey = os.Getenv("DEEPSEEK_API_KEY")
	}

	// Log API key status (truncated for security)
	if apiKey != "" {
		maskedKey := "****"
		if len(apiKey) > 8 {
			maskedKey = apiKey[:4] + "..." + apiKey[len(apiKey)-4:]
		}
		logDebug("Using API key: %s", maskedKey)
	} else {
		logDebug("No API key found, using mock key for testing")
		os.Setenv("XAI_API_KEY", "mock-api-key-for-testing")
	}

	// Always enable LLM for testing
	os.Setenv("NOIDEA_LLM_ENABLED", "true")
	logDebug("NOIDEA_LLM_ENABLED set to: true")

	// Check if this is a suggest test suite
	isSuggestTestSuite := strings.Contains(strings.ToLower(suite.Name), "suggestion") ||
		strings.Contains(strings.ToLower(suite.Name), "suggest")

	// If this is a suggest test suite, set up the test repository
	if isSuggestTestSuite {
		logDebug("Detected suggest test suite, setting up test repository...")

		// Make setup script executable
		chmod := exec.Command("chmod", "+x", "./setup_test_repo.sh")
		if chmodOut, err := chmod.CombinedOutput(); err != nil {
			logDebug("Error making setup script executable: %v\n%s", err, string(chmodOut))
		}

		// Run setup script
		setupCmd := exec.Command("./setup_test_repo.sh")
		setupOutput, err := setupCmd.CombinedOutput()
		if err != nil {
			logDebug("Error setting up test repository: %v\n%s", err, string(setupOutput))
			return fmt.Errorf("failed to set up test repository: %w", err)
		}

		logDebug("Test repository setup output:\n%s", string(setupOutput))

		// Check if the test repo has been initialized properly
		checkCmd := exec.Command("ls", "-la", "test_repo")
		checkOutput, err := checkCmd.CombinedOutput()
		if err == nil {
			logDebug("Test repo contents:\n%s", string(checkOutput))
		}
	}

	// Run each test case
	for _, testCase := range suite.TestCases {
		logDebug("Running test case: %s", testCase.Name)

		// Add test case to summary
		fmt.Fprintf(summary, "## %s\n", testCase.Name)
		fmt.Fprintf(summary, "Description: %s\n", testCase.Description)
		fmt.Fprintf(summary, "Command: `%s %s`\n", testCase.Command, strings.Join(testCase.Args, " "))
		fmt.Fprintf(summary, "Repetitions: %d\n\n", testCase.Repetitions)

		// Create directory for test case results
		testCaseDir := filepath.Join(outputDir, testCase.Name)
		os.MkdirAll(testCaseDir, 0755)

		// Save info file
		infoFile := filepath.Join(testCaseDir, "info.txt")
		info, err := os.Create(infoFile)
		if err != nil {
			return err
		}

		fmt.Fprintf(info, "Test Case: %s\n", testCase.Name)
		fmt.Fprintf(info, "Description: %s\n", testCase.Description)
		fmt.Fprintf(info, "Command: %s %s\n", testCase.Command, strings.Join(testCase.Args, " "))
		fmt.Fprintf(info, "Repetitions: %d\n", testCase.Repetitions)
		info.Close()

		// If this is a suggest test suite, prepare the test repository
		if isSuggestTestSuite {
			if err := prepareTestRepo(testCase.Name); err != nil {
				logDebug("Error preparing test repository for %s: %v", testCase.Name, err)
				fmt.Printf("  Error preparing test repository: %v\n", err)
				fmt.Fprintf(summary, "Error preparing test repository: %v\n", err)
				continue
			}
			logDebug("Test repository prepared for case: %s", testCase.Name)
		}

		// Run the command multiple times
		for i := 1; i <= testCase.Repetitions; i++ {
			logDebug("  Run %d/%d for %s...", i, testCase.Repetitions, testCase.Name)

			// Run the command
			var cmd *exec.Cmd
			if isSuggestTestSuite {
				// For suggest tests, use absolute path to noidea
				absPath, err := filepath.Abs("../noidea")
				if err != nil {
					logDebug("Error getting absolute path: %v", err)
					absPath = "../noidea" // Fallback
				}

				// Special handling for interactive mode
				if testCase.Name == "suggest_interactive_mode" {
					logDebug("  Special handling for interactive mode")

					// Use a different approach for interactive mode with pipes
					cmd = exec.Command(absPath, testCase.Args...)
					cmd.Dir = "test_repo"

					// Create pipes for stdin/stdout/stderr
					stdin, err := cmd.StdinPipe()
					if err != nil {
						logDebug("  Error creating stdin pipe: %v", err)
						continue
					}

					stdout, err := cmd.StdoutPipe()
					if err != nil {
						logDebug("  Error creating stdout pipe: %v", err)
						continue
					}

					stderr, err := cmd.StderrPipe()
					if err != nil {
						logDebug("  Error creating stderr pipe: %v", err)
						continue
					}

					// Start the command
					if err := cmd.Start(); err != nil {
						logDebug("  Error starting interactive command: %v", err)
						continue
					}

					logDebug("  Interactive command started, waiting to send input")

					// Create buffers for output
					var stdoutBuf, stderrBuf strings.Builder

					// Start goroutines to read output
					outputDone := make(chan bool, 2)

					go func() {
						io.Copy(&stdoutBuf, stdout)
						outputDone <- true
					}()

					go func() {
						io.Copy(&stderrBuf, stderr)
						outputDone <- true
					}()

					// Wait for some output before sending input
					time.Sleep(1 * time.Second)

					// Write "y" to simulate user input
					logDebug("  Sending 'y' input to interactive command")
					io.WriteString(stdin, "y\n")
					stdin.Close()

					// Wait for command to complete
					err = cmd.Wait()
					if err != nil {
						logDebug("  Error during interactive command execution: %v", err)
					}

					// Wait for output goroutines to finish
					for i := 0; i < 2; i++ {
						<-outputDone
					}

					// Combine output
					output := stdoutBuf.String() + stderrBuf.String()

					// Save output to file
					outputFile := filepath.Join(testCaseDir, fmt.Sprintf("run_%d.txt", i))
					err = os.WriteFile(outputFile, []byte(output), 0644)
					if err != nil {
						logDebug("  Error saving interactive output: %v", err)
					}

					logDebug("  Interactive test completed for run %d", i)
					continue
				} else {
					// Regular command execution
					cmd = exec.Command(absPath, testCase.Args...)
					cmd.Dir = "test_repo"
					logDebug("  Using command: %s %s (in directory: test_repo)", absPath, strings.Join(testCase.Args, " "))
				}
			} else {
				cmd = exec.Command(testCase.Command, testCase.Args...)
				logDebug("  Using command: %s %s", testCase.Command, strings.Join(testCase.Args, " "))
			}

			// For regular (non-interactive) command execution
			// Capture environment for debugging
			cmd.Env = os.Environ()

			// Capture output
			output, err := cmd.CombinedOutput()

			// If there was an error, log it
			if err != nil {
				logDebug("  Command execution error: %v", err)
				output = append(output, []byte(fmt.Sprintf("\nError: %v\n", err))...)
			}

			logDebug("  Command output length: %d bytes", len(output))
			if len(output) > 0 {
				sampleOutput := string(output)
				if len(sampleOutput) > 500 {
					sampleOutput = sampleOutput[:500] + "... (truncated)"
				}
				logDebug("  Sample output: %s", sampleOutput)
			} else {
				logDebug("  WARNING: Empty output from command")
			}

			// Save output to file
			outputFile := filepath.Join(testCaseDir, fmt.Sprintf("run_%d.txt", i))
			err = os.WriteFile(outputFile, output, 0644)
			if err != nil {
				logDebug("  Error saving output: %v", err)
				fmt.Printf("  Error saving output: %v\n", err)
			}
		}
	}

	logDebug("Test suite completed: %s", suite.Name)
	fmt.Printf("Test suite completed. Results saved to: %s\n", outputDir)
	return nil
}

// CreateDefaultTestSuites creates default test suites for each main feature
func CreateDefaultTestSuites() error {
	// Create test suites directory
	suiteDir := "test_suites"
	err := os.MkdirAll(suiteDir, 0755)
	if err != nil {
		return fmt.Errorf("failed to create test suites directory: %w", err)
	}

	// Summary command test suite
	summarySuite := TestSuite{
		Name:      "Summary Command Tests",
		OutputDir: "results/summary",
		TestCases: []TestCase{
			{
				Name:        "default_summary",
				Command:     "../noidea",
				Args:        []string{"summary"},
				Description: "Default summary command with default settings",
				Repetitions: 3,
			},
			{
				Name:        "summary_14_days",
				Command:     "../noidea",
				Args:        []string{"summary", "--days", "14"},
				Description: "Summary for the last 14 days",
				Repetitions: 3,
			},
			{
				Name:        "summary_snarky_reviewer",
				Command:     "../noidea",
				Args:        []string{"summary", "--personality", "snarky_reviewer"},
				Description: "Summary with snarky reviewer personality",
				Repetitions: 3,
			},
			{
				Name:        "summary_supportive_mentor",
				Command:     "../noidea",
				Args:        []string{"summary", "--personality", "supportive_mentor"},
				Description: "Summary with supportive mentor personality",
				Repetitions: 3,
			},
			{
				Name:        "summary_git_expert",
				Command:     "../noidea",
				Args:        []string{"summary", "--personality", "git_expert"},
				Description: "Summary with git expert personality",
				Repetitions: 3,
			},
			{
				Name:        "summary_markdown_export",
				Command:     "../noidea",
				Args:        []string{"summary", "--export", "markdown"},
				Description: "Summary with markdown export",
				Repetitions: 2,
			},
			{
				Name:        "summary_html_export",
				Command:     "../noidea",
				Args:        []string{"summary", "--export", "html"},
				Description: "Summary with HTML export",
				Repetitions: 2,
			},
			{
				Name:        "summary_stats_only",
				Command:     "../noidea",
				Args:        []string{"summary", "--stats-only"},
				Description: "Summary with statistics only (no AI insights)",
				Repetitions: 1,
			},
		},
	}

	// Moai command test suite
	moaiSuite := TestSuite{
		Name:      "Moai Command Tests",
		OutputDir: "results/moai",
		TestCases: []TestCase{
			{
				Name:        "default_moai",
				Command:     "../noidea",
				Args:        []string{"moai", "Test commit message"},
				Description: "Default moai command with static message",
				Repetitions: 5,
			},
			{
				Name:        "moai_with_ai",
				Command:     "../noidea",
				Args:        []string{"moai", "--ai", "Feature implementation complete"},
				Description: "Moai with AI feedback enabled",
				Repetitions: 5,
			},
			{
				Name:        "moai_with_diff",
				Command:     "../noidea",
				Args:        []string{"moai", "--ai", "--diff", "Bug fix for critical issue"},
				Description: "Moai with diff context",
				Repetitions: 3,
			},
			{
				Name:        "moai_snarky_reviewer",
				Command:     "../noidea",
				Args:        []string{"moai", "--ai", "--personality", "snarky_reviewer", "Code cleanup"},
				Description: "Moai with snarky reviewer personality",
				Repetitions: 5,
			},
			{
				Name:        "moai_supportive_mentor",
				Command:     "../noidea",
				Args:        []string{"moai", "--ai", "--personality", "supportive_mentor", "First attempt at new feature"},
				Description: "Moai with supportive mentor personality",
				Repetitions: 5,
			},
			{
				Name:        "moai_git_expert",
				Command:     "../noidea",
				Args:        []string{"moai", "--ai", "--personality", "git_expert", "Merge branch 'feature/x' into main"},
				Description: "Moai with git expert personality",
				Repetitions: 5,
			},
			{
				Name:        "moai_with_history",
				Command:     "../noidea",
				Args:        []string{"moai", "--ai", "--history", "Follow-up fix"},
				Description: "Moai with commit history context",
				Repetitions: 3,
			},
		},
	}

	// Suggest command test suite
	suggestSuite := TestSuite{
		Name:      "Commit Suggestion Tests",
		OutputDir: "results/suggest",
		TestCases: []TestCase{
			{
				Name:        "default_suggest",
				Command:     "../../noidea",
				Args:        []string{"suggest"},
				Description: "Default suggestion command with current staged changes",
				Repetitions: 5,
			},
			{
				Name:        "suggest_with_history",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--history", "20"},
				Description: "Suggestion with extended commit history context (20 commits)",
				Repetitions: 3,
			},
			{
				Name:        "suggest_with_full_diff",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--full-diff"},
				Description: "Suggestion with full diff context for better analysis",
				Repetitions: 3,
			},
			{
				Name:        "suggest_for_simple_change",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--quiet"},
				Description: "Simple change scenario - should generate single-line commit message",
				Repetitions: 5,
			},
			{
				Name:        "suggest_for_complex_change",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--full-diff"},
				Description: "Complex change scenario - should generate multi-line commit message with body",
				Repetitions: 5,
			},
			{
				Name:        "suggest_interactive_mode",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--interactive"},
				Description: "Test interactive suggestion mode (will require mock input handling)",
				Repetitions: 3,
			},
			{
				Name:        "suggest_with_file_output",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--file", "test_commit_msg.txt"},
				Description: "Suggestion with output to a commit message file",
				Repetitions: 3,
			},
			{
				Name:        "suggest_no_staged_changes",
				Command:     "../../noidea",
				Args:        []string{"suggest"},
				Description: "Behavior when no changes are staged",
				Repetitions: 3,
			},
			{
				Name:        "suggest_with_type_prefix",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--quiet"},
				Description: "Check conventional commit format with type prefix (feat, fix, etc.)",
				Repetitions: 5,
			},
			{
				Name:        "suggest_with_breaking_change",
				Command:     "../../noidea",
				Args:        []string{"suggest", "--full-diff"},
				Description: "Suggestion for changes that include breaking changes",
				Repetitions: 3,
			},
			{
				Name:        "suggest_large_file",
				Command:     "../../noidea",
				Args:        []string{"suggest"},
				Description: "Suggestion with a large file (10,000 lines)",
				Repetitions: 2,
			},
			{
				Name:        "suggest_non_english",
				Command:     "../../noidea",
				Args:        []string{"suggest"},
				Description: "Suggestion with a Go file containing German comments",
				Repetitions: 2,
			},
		},
	}

	// Save the test suites
	err = SaveTestSuite(summarySuite, filepath.Join(suiteDir, "summary_tests.json"))
	if err != nil {
		return fmt.Errorf("failed to save summary test suite: %w", err)
	}

	err = SaveTestSuite(moaiSuite, filepath.Join(suiteDir, "moai_tests.json"))
	if err != nil {
		return fmt.Errorf("failed to save moai test suite: %w", err)
	}

	err = SaveTestSuite(suggestSuite, filepath.Join(suiteDir, "suggest_tests.json"))
	if err != nil {
		return fmt.Errorf("failed to save suggest test suite: %w", err)
	}

	fmt.Println("Default test suites created in:", suiteDir)
	return nil
}

// Helper to generate and run a commit simulation with different messages
func RunCommitSimulation() error {
	// Create a temporary test repo
	testRepoDir := "test_repo"
	resultsDir := "results/commits"

	// Create dirs
	os.MkdirAll(testRepoDir, 0755)
	os.MkdirAll(resultsDir, 0755)

	// Try to load .env file from project root
	LoadEnvFile("../.env")

	// Check if we have an API key, if not use a mock one
	apiKey := os.Getenv("XAI_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
	}
	if apiKey == "" {
		apiKey = os.Getenv("DEEPSEEK_API_KEY")
	}

	// Log API key status (truncated for security)
	if apiKey != "" {
		maskedKey := "****"
		if len(apiKey) > 8 {
			maskedKey = apiKey[:4] + "..." + apiKey[len(apiKey)-4:]
		}
		fmt.Printf("Using API key: %s\n", maskedKey)
	} else {
		fmt.Println("No API key found, using mock key for testing")
		os.Setenv("XAI_API_KEY", "mock-api-key-for-testing")
	}

	// Always enable LLM for testing
	os.Setenv("NOIDEA_LLM_ENABLED", "true")

	// Navigate to test repo dir
	currentDir, err := os.Getwd()
	if err != nil {
		return err
	}

	testRepoAbsPath := filepath.Join(currentDir, testRepoDir)
	fmt.Printf("Test repo path: %s\n", testRepoAbsPath)

	// Set up Git repo if it doesn't exist
	if _, err := os.Stat(filepath.Join(testRepoDir, ".git")); os.IsNotExist(err) {
		fmt.Println("Initializing new git repository...")

		// Initialize Git repo
		cmd := exec.Command("git", "init")
		cmd.Dir = testRepoDir
		err = cmd.Run()
		if err != nil {
			return fmt.Errorf("failed to init git repo: %w", err)
		}

		// Set up Git config
		cmd = exec.Command("git", "config", "user.name", "Test User")
		cmd.Dir = testRepoDir
		err = cmd.Run()
		if err != nil {
			return err
		}

		cmd = exec.Command("git", "config", "user.email", "test@example.com")
		cmd.Dir = testRepoDir
		err = cmd.Run()
		if err != nil {
			return err
		}

		// Create README
		err = os.WriteFile(filepath.Join(testRepoDir, "README.md"),
			[]byte("# Test Repository\n\nThis is a test repository for noidea commit simulations.\n"), 0644)
		if err != nil {
			return err
		}

		// Initial commit
		cmd = exec.Command("git", "add", "README.md")
		cmd.Dir = testRepoDir
		err = cmd.Run()
		if err != nil {
			return err
		}

		cmd = exec.Command("git", "commit", "-m", "Initial commit")
		cmd.Dir = testRepoDir
		err = cmd.Run()
		if err != nil {
			return err
		}

		// Install noidea
		absPath, err := filepath.Abs("../noidea")
		if err != nil {
			return fmt.Errorf("failed to get absolute path: %w", err)
		}

		fmt.Printf("Using noidea binary (absolute path): %s\n", absPath)

		cmd = exec.Command(absPath, "init")
		cmd.Dir = testRepoDir
		initOutput, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("failed to install noidea: %w\nOutput: %s", err, string(initOutput))
		}
		fmt.Printf("noidea initialized in test repo: %s\n", string(initOutput))
	}

	// Test commit messages
	commitMessages := []string{
		"Add new feature X",
		"Fix bug in login flow",
		"Refactor authentication module",
		"Update documentation for API",
		"Performance optimization for database queries",
		"Remove deprecated code",
		"Merge branch 'feature/y' into main",
		"CSS styling updates",
		"Add unit tests",
		"Version bump to 1.2.0",
	}

	// Perform commits
	for i, message := range commitMessages {
		// Create a test file
		filename := fmt.Sprintf("test_file_%d.txt", i+1)
		filePath := filepath.Join(testRepoDir, filename)
		err = os.WriteFile(filePath, []byte(fmt.Sprintf("Test content for %s\n", filename)), 0644)
		if err != nil {
			return err
		}

		// Add the file
		addCmd := exec.Command("git", "add", filename)
		addCmd.Dir = testRepoDir
		err = addCmd.Run()
		if err != nil {
			return fmt.Errorf("failed to add file %s: %w", filename, err)
		}

		// Commit with output capture
		outputFile := filepath.Join(resultsDir, fmt.Sprintf("commit_%d.txt", i+1))
		commitCmd := exec.Command("git", "commit", "-m", message)
		commitCmd.Dir = testRepoDir

		// Capture stdout and stderr
		commitOutput, err := commitCmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("failed commit %d: %w", i+1, err)
		}

		// Save the output
		err = os.WriteFile(outputFile, commitOutput, 0644)
		if err != nil {
			return fmt.Errorf("failed to write output file: %w", err)
		}

		fmt.Printf("Commit %d/%d completed\n", i+1, len(commitMessages))

		// Sleep briefly to avoid rate limits on API calls
		time.Sleep(500 * time.Millisecond)
	}

	fmt.Printf("Commit simulation completed. Results saved to: %s\n", resultsDir)
	return nil
}

// Helper to compare results and generate a comparison report
func GenerateComparisonReport(resultsDir string, outputFile string) error {
	// Parse all test results and generate a comparison report
	report, err := os.Create(outputFile)
	if err != nil {
		return fmt.Errorf("failed to create report file: %w", err)
	}
	defer report.Close()

	fmt.Fprintf(report, "# noidea Test Results Comparison\n\n")
	fmt.Fprintf(report, "Generated: %s\n\n", time.Now().Format(time.RFC3339))

	// Walk through the results directory
	err = filepath.Walk(resultsDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Skip directories
		if info.IsDir() {
			return nil
		}

		// Only process .txt files
		if !strings.HasSuffix(info.Name(), ".txt") {
			return nil
		}

		// Get relative path
		relPath, err := filepath.Rel(resultsDir, path)
		if err != nil {
			return err
		}

		// Read file content
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}

		// Add to report
		fmt.Fprintf(report, "## %s\n\n", relPath)
		fmt.Fprintf(report, "```\n%s\n```\n\n", content)

		return nil
	})

	if err != nil {
		return fmt.Errorf("failed to walk results directory: %w", err)
	}

	fmt.Printf("Comparison report generated: %s\n", outputFile)
	return nil
}

// LoadEnvFile loads environment variables from a .env file
func LoadEnvFile(path string) {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Printf("Warning: Could not read .env file: %v\n", err)
		return
	}

	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])

		// Skip if variable is already set in environment
		if _, exists := os.LookupEnv(key); !exists {
			os.Setenv(key, value)
		}
	}
}

// prepareTestRepo prepares a test repository with appropriate staged changes
// based on the test case name for commit suggestion tests
func prepareTestRepo(testCaseName string) error {
	// Create a temporary test repo directory
	testRepoDir := "test_repo"
	os.MkdirAll(testRepoDir, 0755)

	// Check if .git directory exists, if not initialize repo
	if _, err := os.Stat(filepath.Join(testRepoDir, ".git")); os.IsNotExist(err) {
		fmt.Println("Initializing test repository...")
		cmd := exec.Command("git", "init")
		cmd.Dir = testRepoDir
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to initialize git repository: %w", err)
		}

		// Set git user name and email if not set
		cmd = exec.Command("git", "config", "user.name", "Test User")
		cmd.Dir = testRepoDir
		cmd.Run()

		cmd = exec.Command("git", "config", "user.email", "test@example.com")
		cmd.Dir = testRepoDir
		cmd.Run()
	}

	// Clean the repo to start fresh
	cmd := exec.Command("git", "clean", "-fd")
	cmd.Dir = testRepoDir
	cmd.Run()

	// Reset any staged changes
	cmd = exec.Command("git", "reset", "--hard", "HEAD")
	cmd.Dir = testRepoDir
	// Ignore errors since repo might be empty

	// Clean staging area
	cmd = exec.Command("git", "reset")
	cmd.Dir = testRepoDir
	cmd.Run()

	// Create or modify files based on test case
	switch testCaseName {
	case "default_suggest", "suggest_with_history", "suggest_with_file_output", "suggest_with_type_prefix":
		// Simple change - single file modification
		writeFile(filepath.Join(testRepoDir, "README.md"), "# Test Repository\n\nThis is a simple change for testing commit suggestions.")

		// Stage the change
		cmd := exec.Command("git", "add", "README.md")
		cmd.Dir = testRepoDir
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to stage changes: %w", err)
		}

	case "suggest_with_full_diff", "suggest_for_complex_change":
		// Complex changes - multiple files with substantive changes that should generate a multi-line commit message

		// 1. A new module with multiple components for a user authentication system
		os.MkdirAll(filepath.Join(testRepoDir, "auth"), 0755)

		// User model file
		userGoContent := `package auth

// User represents a user in the authentication system
type User struct {
	ID        string
	Username  string
	Email     string
	Password  string // Hashed password
	Active    bool
	CreatedAt int64
	UpdatedAt int64
}

// NewUser creates a new user instance
func NewUser(username, email, password string) *User {
	now := time.Now().Unix()
	return &User{
		ID:        GenerateUUID(),
		Username:  username,
		Email:     email,
		Password:  HashPassword(password),
		Active:    true,
		CreatedAt: now,
		UpdatedAt: now,
	}
}
`
		writeFile(filepath.Join(testRepoDir, "auth/user.go"), userGoContent)

		// Authentication service
		serviceGoContent := `package auth

// AuthService provides authentication functionality
type AuthService struct {
	repo UserRepository
}

// NewAuthService creates a new authentication service
func NewAuthService(repo UserRepository) *AuthService {
	return &AuthService{
		repo: repo,
	}
}

// Login attempts to authenticate a user
func (s *AuthService) Login(username, password string) (*User, error) {
	user, err := s.repo.FindByUsername(username)
	if err != nil {
		return nil, ErrUserNotFound
	}
	
	if !VerifyPassword(user.Password, password) {
		return nil, ErrInvalidCredentials
	}
	
	return user, nil
}

// Register creates a new user
func (s *AuthService) Register(username, email, password string) (*User, error) {
	// Check if user already exists
	existing, _ := s.repo.FindByUsername(username)
	if existing != nil {
		return nil, ErrUserAlreadyExists
	}
	
	// Create new user
	user := NewUser(username, email, password)
	
	// Save to repository
	err := s.repo.Save(user)
	if err != nil {
		return nil, err
	}
	
	return user, nil
}
`
		writeFile(filepath.Join(testRepoDir, "auth/service.go"), serviceGoContent)

		// Repository interface
		repoGoContent := `package auth

// UserRepository defines the interface for user data storage
type UserRepository interface {
	// FindByID retrieves a user by ID
	FindByID(id string) (*User, error)
	
	// FindByUsername retrieves a user by username
	FindByUsername(username string) (*User, error)
	
	// Save stores a user in the repository
	Save(user *User) error
	
	// Update updates an existing user
	Update(user *User) error
	
	// Delete removes a user from the repository
	Delete(id string) error
}

// Common repository errors
var (
	ErrUserNotFound      = errors.New("user not found")
	ErrUserAlreadyExists = errors.New("user already exists") 
	ErrInvalidCredentials = errors.New("invalid credentials")
)
`
		writeFile(filepath.Join(testRepoDir, "auth/repository.go"), repoGoContent)

		// Helpers file
		helpersGoContent := `package auth

import (
	"crypto/rand"
	"encoding/hex"
	"golang.org/x/crypto/bcrypt"
)

// GenerateUUID creates a random UUID
func GenerateUUID() string {
	b := make([]byte, 16)
	_, err := rand.Read(b)
	if err != nil {
		return "error"
	}
	return hex.EncodeToString(b)
}

// HashPassword creates a bcrypt hash of a password
func HashPassword(password string) string {
	hashed, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return ""
	}
	return string(hashed)
}

// VerifyPassword checks if a password matches a hash
func VerifyPassword(hash, password string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	return err == nil
}
`
		writeFile(filepath.Join(testRepoDir, "auth/helpers.go"), helpersGoContent)

		// Main app file using the auth package
		appGoContent := `package main

import (
	"fmt"
	"log"
	"os"
	"./auth"
)

func main() {
	// Initialize auth service
	repo := NewMemoryUserRepository()
	authService := auth.NewAuthService(repo)
	
	// Register a user
	user, err := authService.Register("testuser", "test@example.com", "password123")
	if err != nil {
		log.Fatalf("Failed to register user: %v", err)
	}
	
	fmt.Printf("User registered: %s\n", user.Username)
	
	// Login
	loggedUser, err := authService.Login("testuser", "password123")
	if err != nil {
		log.Fatalf("Login failed: %v", err)
	}
	
	fmt.Printf("Login successful: %s\n", loggedUser.Username)
}

// In-memory implementation for testing
type MemoryUserRepository struct {
	users map[string]*auth.User
}

func NewMemoryUserRepository() *MemoryUserRepository {
	return &MemoryUserRepository{
		users: make(map[string]*auth.User),
	}
}

// Implement the repository interface...
`
		writeFile(filepath.Join(testRepoDir, "app.go"), appGoContent)

		// Update README with project details
		readmeContent := `# Authentication System

A secure authentication system with the following features:

- User registration and login
- Password hashing with bcrypt
- Flexible repository interface for multiple storage options
- Simple API for integration with any application

## Getting Started

Install dependencies:
` + "```" + `
go get golang.org/x/crypto/bcrypt
` + "```" + `

## Usage Examples

See the app.go file for a complete example of using the authentication system.
`
		writeFile(filepath.Join(testRepoDir, "README.md"), readmeContent)

		// Stage all changes
		cmd := exec.Command("git", "add", ".")
		cmd.Dir = testRepoDir
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to stage complex changes: %w", err)
		}

	case "suggest_for_simple_change":
		// Very simple change - single line modification
		writeFile(filepath.Join(testRepoDir, "simple.txt"), "This is a simple text file with a small change.")

		// Stage the change
		cmd := exec.Command("git", "add", "simple.txt")
		cmd.Dir = testRepoDir
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to stage simple change: %w", err)
		}

	case "suggest_with_breaking_change":
		// First, create an initial version of the API file and commit it
		// This way we'll have a base version to compare against to detect breaking changes
		apiV1Content := `package api

// UserData represents user information in the system
type UserData struct {
	ID       string
	Username string
	Email    string
	Active   bool
}

// GetUser retrieves a user by ID
func GetUser(id string) UserData {
	// Implementation
	return UserData{}
}

// CreateUser adds a new user to the system
func CreateUser(username, email string) UserData {
	// Implementation
	return UserData{
		Username: username,
		Email:    email,
		Active:   true,
	}
}

// API version constant
const APIVersion = "v1.0"`

		writeFile(filepath.Join(testRepoDir, "api.go"), apiV1Content)

		// Add and commit initial version
		cmd := exec.Command("git", "add", "api.go")
		cmd.Dir = testRepoDir
		cmd.Run()

		cmd = exec.Command("git", "commit", "-m", "Initial API implementation")
		cmd.Dir = testRepoDir
		cmd.Run()

		// Now create the breaking changes version
		apiV2Content := `package api

// UserData represents user information in the system
// Breaking change: Removed Username field, added FirstName and LastName
type UserData struct {
	ID        string
	FirstName string // Added in v2.0
	LastName  string // Added in v2.0
	Email     string
	Active    bool
}

// GetUser retrieves a user by ID
// Breaking change: Now returns error as second value
func GetUser(id string) (UserData, error) {
	// Implementation
	return UserData{}, nil
}

// CreateUser adds a new user to the system
// Breaking change: Now accepts firstName and lastName instead of username
func CreateUser(firstName, lastName, email string) (UserData, error) {
	// Implementation
	return UserData{
		FirstName: firstName,
		LastName:  lastName,
		Email:     email,
		Active:    true,
	}, nil
}

// DeleteUser removes a user from the system
// New method in v2.0
func DeleteUser(id string) error {
	// Implementation
	return nil
}

// API version constant
// Breaking change: Version bumped to reflect breaking changes
const APIVersion = "v2.0"`

		writeFile(filepath.Join(testRepoDir, "api.go"), apiV2Content)

		// Add explicit breaking change notice in a CHANGELOG file
		changelogContent := `# Changelog

## v2.0.0 - Breaking Changes

- **UserData struct**: Removed Username field, replaced with FirstName and LastName
- **GetUser function**: Now returns an error as second return value
- **CreateUser function**: Now takes firstName and lastName instead of username
- **Added DeleteUser function**: New functionality to remove users
`
		writeFile(filepath.Join(testRepoDir, "CHANGELOG.md"), changelogContent)

		// Stage the breaking changes
		cmd = exec.Command("git", "add", "api.go", "CHANGELOG.md")
		cmd.Dir = testRepoDir
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to stage breaking changes: %w", err)
		}

	case "suggest_interactive_mode":
		// For interactive mode, create a small feature implementation
		// Note: The test framework will handle the interactive part separately

		// First create a base file and commit it
		featureV1Content := `package feature

// Feature is a cool new feature
type Feature struct {
	Name        string
	Description string
	Enabled     bool
}

// NewFeature creates a new feature
func NewFeature(name, description string) *Feature {
	return &Feature{
		Name:        name,
		Description: description,
		Enabled:     false,
	}
}

// Enable activates the feature
func (f *Feature) Enable() {
	f.Enabled = true
}

// IsEnabled checks if feature is enabled
func (f *Feature) IsEnabled() bool {
	return f.Enabled
}`

		writeFile(filepath.Join(testRepoDir, "feature.go"), featureV1Content)

		// Add and commit initial version
		cmd := exec.Command("git", "add", "feature.go")
		cmd.Dir = testRepoDir
		cmd.Run()

		cmd = exec.Command("git", "commit", "-m", "Initial feature implementation")
		cmd.Dir = testRepoDir
		cmd.Run()

		// Now implement a new feature enhancement
		featureV2Content := `package feature

// Feature is a cool new feature
type Feature struct {
	Name        string
	Description string
	Enabled     bool
	Priority    int    // Added priority field
	Tags        []string // Added tags field
}

// NewFeature creates a new feature
func NewFeature(name, description string, priority int) *Feature {
	return &Feature{
		Name:        name,
		Description: description,
		Enabled:     false,
		Priority:    priority,
		Tags:        []string{},
	}
}

// Enable activates the feature
func (f *Feature) Enable() {
	f.Enabled = true
}

// IsEnabled checks if feature is enabled
func (f *Feature) IsEnabled() bool {
	return f.Enabled
}

// AddTag adds a tag to the feature
func (f *Feature) AddTag(tag string) {
	f.Tags = append(f.Tags, tag)
}

// HasTag checks if feature has a specific tag
func (f *Feature) HasTag(tag string) bool {
	for _, t := range f.Tags {
		if t == tag {
			return true
		}
	}
	return false
}`

		writeFile(filepath.Join(testRepoDir, "feature.go"), featureV2Content)

		// Stage the changes
		cmd = exec.Command("git", "add", "feature.go")
		cmd.Dir = testRepoDir
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("failed to stage feature changes: %w", err)
		}

		// For interactive mode testing, we need to provide input to the command
		// Add a special flag to a file for the test framework to detect
		writeFile(filepath.Join(testRepoDir, ".interactive_test"), "yes\n")

	case "suggest_no_staged_changes":
		// For this specific test, we intentionally don't stage any changes
		// Just create a file but don't add it
		writeFile(filepath.Join(testRepoDir, "unstaged.txt"), "This file is intentionally not staged.")
		fmt.Println("Not staging any changes for the 'suggest_no_staged_changes' test case...")

	case "suggest_large_file":
		// Large file test - create a large text file with 10,000 lines
		largeContent := strings.Repeat("Line of dummy code for large file test: func dummy() { fmt.Println(\"test\"); }\n", 10000)
		writeFile(filepath.Join(testRepoDir, "large_file.go"), largeContent)
		// Stage the large file
		cmd := exec.Command("git", "add", "large_file.go")
		cmd.Dir = testRepoDir
		cmd.Run()

	case "suggest_non_english":
		// Non-English comments - create a Go file with German comments
		nonEnglishContent := `package main

// Dies ist eine Testdatei mit deutschen Kommentaren
// Funktion zum Testen der Sprachunterstützung
func TestFunction() string {
    // Diese Funktion gibt eine Begrüßung zurück
    return "Hallo Welt"
}

// Eine weitere Funktion mit mehr Kommentaren
// Um zu testen, ob die AI mit Nicht-Englisch umgehen kann
func AnotherTest() {
    // Dummy implementation
    fmt.Println("Test")
}`
		writeFile(filepath.Join(testRepoDir, "non_english.go"), nonEnglishContent)
		// Stage the file
		cmd := exec.Command("git", "add", "non_english.go")
		cmd.Dir = testRepoDir
		cmd.Run()
	}

	fmt.Println("Test repository prepared with appropriate staged changes for:", testCaseName)
	return nil
}

// Helper function to write content to a file
func writeFile(path, content string) error {
	return os.WriteFile(path, []byte(content), 0644)
}

func main() {
	// Make sure results directory exists
	err := os.MkdirAll("results", 0755)
	if err != nil {
		fmt.Printf("Error creating results directory: %v\n", err)
		os.Exit(1)
	}

	// Parse command line arguments
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run simulation_tester.go [create|run|commit|compare]")
		fmt.Println("  create    - Create default test suites")
		fmt.Println("  run file  - Run a specific test suite from a JSON file")
		fmt.Println("  run all   - Run all test suites in test_suites directory")
		fmt.Println("  commit    - Run a commit simulation with various commit messages")
		fmt.Println("  compare   - Generate a comparison report of all results")
		os.Exit(1)
	}

	command := os.Args[1]

	switch command {
	case "create":
		err = CreateDefaultTestSuites()
		if err != nil {
			fmt.Printf("Error creating test suites: %v\n", err)
			os.Exit(1)
		}

	case "run":
		if len(os.Args) < 3 {
			fmt.Println("Error: Missing test suite file argument")
			os.Exit(1)
		}

		file := os.Args[2]

		if file == "all" {
			// Run all test suites
			files, err := filepath.Glob("test_suites/*.json")
			if err != nil {
				fmt.Printf("Error finding test suites: %v\n", err)
				os.Exit(1)
			}

			for _, f := range files {
				fmt.Printf("Running test suite: %s\n", f)
				suite, err := LoadTestSuite(f)
				if err != nil {
					fmt.Printf("Error loading test suite %s: %v\n", f, err)
					continue
				}

				err = RunTestSuite(suite)
				if err != nil {
					fmt.Printf("Error running test suite %s: %v\n", f, err)
				}
			}
		} else {
			// Run a specific test suite
			suite, err := LoadTestSuite(file)
			if err != nil {
				fmt.Printf("Error loading test suite: %v\n", err)
				os.Exit(1)
			}

			err = RunTestSuite(suite)
			if err != nil {
				fmt.Printf("Error running test suite: %v\n", err)
				os.Exit(1)
			}
		}

	case "commit":
		err = RunCommitSimulation()
		if err != nil {
			fmt.Printf("Error running commit simulation: %v\n", err)
			os.Exit(1)
		}

	case "compare":
		err = GenerateComparisonReport("results", "results/comparison_report.md")
		if err != nil {
			fmt.Printf("Error generating comparison report: %v\n", err)
			os.Exit(1)
		}

	default:
		fmt.Printf("Unknown command: %s\n", command)
		os.Exit(1)
	}
}
