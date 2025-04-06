package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/AccursedGalaxy/noidea/internal/github"
)

// Flag variables
var (
	forceUpdateFlag bool
)

// updateCmd represents the update command
var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "Check for and apply updates",
	Long: `Check if a new version of noidea is available and update to the latest version.
This command will check GitHub releases and either:
  1. Use 'go install' to update if installed via Go
  2. Download and replace the binary if installed from a release
  3. Provide instructions for other installation methods`,
	Run: func(cmd *cobra.Command, args []string) {
		runUpdate(forceUpdateFlag)
	},
}

func init() {
	rootCmd.AddCommand(updateCmd)
	updateCmd.Flags().BoolVarP(&forceUpdateFlag, "force", "f", false, "Force update even if already on latest version")
}

// runUpdate checks for updates and applies them
func runUpdate(force bool) {
	fmt.Println("Checking for updates...")

	// Check latest version from GitHub
	latestVersion, releaseURL, err := getLatestVersionFromGitHub()
	if err != nil {
		fmt.Printf("Error checking for updates: %s\n", err)
		return
	}

	// Output version information
	fmt.Printf("Current version: %s\n", Version)
	fmt.Printf("Latest version: %s\n", latestVersion)

	// Compare versions to determine if latest is newer
	var latestIsNewer bool = latestVersion != Version

	// If already on latest version and not forcing update, exit
	if !latestIsNewer && !force {
		fmt.Println(color.GreenString("✓ Already running the latest version!"))
		return
	}

	// If on a development version, warn user but allow a forced update
	if strings.Contains(Version, "-") && !latestIsNewer && !force {
		fmt.Println(color.YellowString("You're running a development version that's newer than the latest release."))
		fmt.Println("Use --force to downgrade to the latest stable release.")
		return
	}

	// Check how the tool was installed
	installMethod := detectInstallMethod()

	// Update based on install method
	switch installMethod {
	case "go":
		updateViaGo()
	case "binary":
		updateViaBinary(releaseURL)
	case "package":
		updateViaPackageManager()
	default:
		fmt.Println("Couldn't determine how noidea was installed.")
		fmt.Println("Please update manually following the instructions at:")
		fmt.Printf("  %s\n", releaseURL)
	}
}

// detectInstallMethod tries to determine how noidea was installed
func detectInstallMethod() string {
	// Check if executable path contains Go path
	execPath, err := os.Executable()
	if err == nil {
		if strings.Contains(execPath, "go/bin") {
			return "go"
		}
	}

	// Check if go is available
	_, err = exec.LookPath("go")
	if err == nil {
		// Try to run go list to check if this package is installed via go
		cmd := exec.Command("go", "list", "-m", "github.com/AccursedGalaxy/noidea")
		if err := cmd.Run(); err == nil {
			return "go"
		}
	}

	// Try to detect package manager
	if _, err := exec.LookPath("apt"); err == nil && fileExists("/var/lib/dpkg/info/noidea.list") {
		return "package"
	}
	if _, err := exec.LookPath("yum"); err == nil && fileExists("/var/lib/rpm/Packages") {
		return "package"
	}
	if _, err := exec.LookPath("brew"); err == nil {
		// Check if installed via homebrew
		cmd := exec.Command("brew", "list", "noidea")
		if err := cmd.Run(); err == nil {
			return "package"
		}
	}

	// Default to binary
	return "binary"
}

// updateViaGo updates noidea using go install
func updateViaGo() {
	fmt.Println("Updating via Go...")

	cmd := exec.Command("go", "install", "github.com/AccursedGalaxy/noidea@latest")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Printf("Error updating: %s\n", err)
		return
	}

	fmt.Println(color.GreenString("✓ Successfully updated noidea!"))
	fmt.Println("Restart any open sessions to use the new version.")
}

// updateViaBinary updates noidea by downloading the binary directly
func updateViaBinary(releaseURL string) {
	fmt.Println("Updating via binary download...")
	fmt.Printf("Please download the latest version from: %s\n", releaseURL)
	fmt.Println("And replace your current binary.")

	// TODO: Implement automatic binary replacement when secure downloading is implemented
}

// updateViaPackageManager shows instructions for updating via package managers
func updateViaPackageManager() {
	fmt.Println("Please update using your package manager:")

	if _, err := exec.LookPath("apt"); err == nil {
		fmt.Println("  sudo apt update && sudo apt upgrade noidea")
	} else if _, err := exec.LookPath("yum"); err == nil {
		fmt.Println("  sudo yum update noidea")
	} else if _, err := exec.LookPath("brew"); err == nil {
		fmt.Println("  brew upgrade noidea")
	} else {
		fmt.Println("  Please use your system's package manager to update")
	}
}

// getLatestVersionFromGitHub checks GitHub releases for the latest version
func getLatestVersionFromGitHub() (string, string, error) {
	// Create a GitHub client
	client, err := github.NewClient()
	if err != nil {
		// If auth fails, create an unauthenticated client for public repos
		client = github.NewClientWithoutAuth()
	}

	// Get latest release
	owner := "AccursedGalaxy"
	repo := "noidea"
	release, err := client.GetLatestRelease(owner, repo)
	if err != nil {
		return "", "", err
	}

	// Extract version and URL
	tagName, ok := release["tag_name"].(string)
	if !ok {
		return "", "", fmt.Errorf("unable to get tag name from release")
	}

	htmlURL, ok := release["html_url"].(string)
	if !ok {
		htmlURL = fmt.Sprintf("https://github.com/%s/%s/releases/latest", owner, repo)
	}

	return tagName, htmlURL, nil
}

// fileExists checks if a file exists
func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
