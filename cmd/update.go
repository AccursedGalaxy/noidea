package cmd

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"golang.org/x/term"

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
	// Get terminal width
	width := 80
	if w, _, err := term.GetSize(0); err == nil && w > 0 {
		width = w
	}

	// Header
	fmt.Println()
	fmt.Println(color.New(color.Bold).Sprintf("🔄 Checking for Updates"))
	fmt.Println(color.HiBlackString(strings.Repeat("━", width/2)))

	// Check latest version from GitHub
	fmt.Printf("  %s ", color.HiBlueString("◉"))
	fmt.Printf("%s\n", color.New(color.Bold).Sprintf("Fetching latest release information..."))

	latestVersion, releaseURL, err := getLatestVersionFromGitHub()
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error checking for updates"),
			err)
		return
	}

	// Output version information in a more visually appealing way
	fmt.Printf("  %s %s: %s\n",
		color.HiMagentaString("◆"),
		color.New(color.Bold).Sprint("Current version"),
		color.CyanString(Version))

	fmt.Printf("  %s %s: %s\n\n",
		color.HiMagentaString("◆"),
		color.New(color.Bold).Sprint("Latest version"),
		color.CyanString(latestVersion))

	// Compare versions to determine if latest is newer
	var latestIsNewer bool
	if strings.Contains(Version, "-") {
		// If current is a development version based on the same release version,
		// then the release version is not newer
		latestIsNewer = !strings.HasPrefix(Version, latestVersion)
	} else {
		// For regular versions, just check if they're different
		latestIsNewer = latestVersion != Version
	}

	// If already on latest version and not forcing update, exit
	if !latestIsNewer && !force {
		fmt.Printf("  %s %s\n\n",
			color.New(color.FgGreen, color.Bold).Sprint("✓"),
			color.New(color.Bold).Sprint("Already running the latest version!"))
		return
	}

	// If on a development version, warn user but allow a forced update
	if strings.Contains(Version, "-") && !latestIsNewer && !force {
		fmt.Printf("  %s %s\n",
			color.New(color.FgYellow, color.Bold).Sprint("⚠️"),
			color.New(color.Bold).Sprint("You're running a development version that's newer than the latest release."))
		fmt.Printf("  Use %s to downgrade to the latest stable release.\n\n",
			color.CyanString("--force"))
		return
	}

	// Check how the tool was installed
	fmt.Printf("  %s %s\n",
		color.HiBlueString("◉"),
		color.New(color.Bold).Sprintf("Determining installation method..."))

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
		fmt.Printf("  %s %s\n",
			color.New(color.FgYellow, color.Bold).Sprint("⚠️"),
			color.New(color.Bold).Sprint("Couldn't determine how noidea was installed."))
		fmt.Println("  Please update manually following the instructions at:")
		fmt.Printf("  %s\n\n", color.CyanString(releaseURL))
	}
}

// detectInstallMethod tries to determine how noidea was installed
func detectInstallMethod() string {
	// Get the executable path
	execPath, err := os.Executable()
	if err != nil {
		// If we can't determine the path, default to binary method
		return "binary"
	}

	// Resolve any symlinks to get the actual binary location
	realPath, err := filepath.EvalSymlinks(execPath)
	if err == nil {
		execPath = realPath
	}

	// Check if executable is in Go's bin directory
	// This is the most reliable indicator of a Go installation
	if strings.Contains(execPath, "go/bin") || strings.Contains(execPath, "go"+string(filepath.Separator)+"bin") {
		return "go"
	}

	// Check if in common system binary directories (likely from make install or binary download)
	systemDirs := []string{
		"/usr/local/bin",
		"/usr/bin",
		"/bin",
	}
	for _, dir := range systemDirs {
		if strings.HasPrefix(execPath, dir) {
			return "binary"
		}
	}

	// Check if in user's bin directory (also likely from make install)
	if homeDir, err := os.UserHomeDir(); err == nil {
		userBinDirs := []string{
			filepath.Join(homeDir, "bin"),
			filepath.Join(homeDir, ".local", "bin"),
		}
		for _, dir := range userBinDirs {
			if strings.HasPrefix(execPath, dir) {
				return "binary"
			}
		}
	}

	// Try to detect package manager installation
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

	// As a last resort, check if installed via go install
	// Only do this if we haven't matched any of the above
	_, err = exec.LookPath("go")
	if err == nil {
		// Check if the binary is in GOPATH/bin or GOBIN
		gopath := os.Getenv("GOPATH")
		if gopath == "" {
			if homeDir, err := os.UserHomeDir(); err == nil {
				gopath = filepath.Join(homeDir, "go")
			}
		}
		gobin := os.Getenv("GOBIN")

		if gobin != "" && strings.HasPrefix(execPath, gobin) {
			return "go"
		}
		if gopath != "" && strings.HasPrefix(execPath, filepath.Join(gopath, "bin")) {
			return "go"
		}
	}

	// Default to binary method for manual installations
	return "binary"
}

// updateViaGo updates noidea using go install
func updateViaGo() {
	fmt.Printf("  %s %s\n",
		color.HiGreenString("◉"),
		color.New(color.Bold).Sprintf("Updating via Go..."))

	cmd := exec.Command("go", "install", "github.com/AccursedGalaxy/noidea@latest")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Printf("  %s %s: %s\n\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error updating"),
			err)
		return
	}

	fmt.Printf("  %s %s\n",
		color.New(color.FgGreen, color.Bold).Sprint("✓"),
		color.New(color.Bold).Sprint("Successfully updated noidea!"))
	fmt.Printf("  %s\n\n",
		color.HiBlackString("Restart any open sessions to use the new version."))
}

// updateViaBinary updates noidea by downloading the binary directly
func updateViaBinary(releaseURL string) {
	fmt.Printf("  %s %s\n",
		color.HiYellowString("◉"),
		color.New(color.Bold).Sprintf("Automatic update starting..."))

	// Get current executable path
	currentExe, err := os.Executable()
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error finding current executable"),
			err)
		fmt.Printf("  Please download manually from: %s\n\n", color.CyanString(releaseURL))
		return
	}

	// Get release info to find download URL for appropriate binary
	client, err := github.NewClient()
	if err != nil {
		client = github.NewClientWithoutAuth()
	}

	// Get latest release with assets
	owner := "AccursedGalaxy"
	repo := "noidea"
	release, err := client.GetLatestRelease(owner, repo)
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error fetching release assets"),
			err)
		fmt.Printf("  Please download manually from: %s\n\n", color.CyanString(releaseURL))
		return
	}

	// Find appropriate asset for this OS/arch
	assetURL, err := findAppropriateAsset(release)
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error finding appropriate binary"),
			err)
		fmt.Printf("  Please download manually from: %s\n\n", color.CyanString(releaseURL))
		return
	}

	// Download binary to temporary file
	fmt.Printf("  %s %s\n",
		color.HiBlueString("◉"),
		color.New(color.Bold).Sprintf("Downloading new version..."))

	tempFile, err := downloadBinary(assetURL)
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error downloading binary"),
			err)
		fmt.Printf("  Please download manually from: %s\n\n", color.CyanString(releaseURL))
		return
	}
	defer os.Remove(tempFile) // Clean up temp file

	// Make temporary file executable
	err = os.Chmod(tempFile, 0755)
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error setting executable permissions"),
			err)
		return
	}

	// Get permissions from original file
	fileInfo, err := os.Stat(currentExe)
	if err == nil {
		// Try to preserve original file permissions
		err = os.Chmod(tempFile, fileInfo.Mode())
		if err != nil {
			// Just warn, not critical
			fmt.Printf("  %s %s\n",
				color.New(color.FgYellow, color.Bold).Sprint("⚠️"),
				color.New(color.Bold).Sprint("Could not preserve file permissions"))
		}
	}

	// Replace current executable with new one
	fmt.Printf("  %s %s\n",
		color.HiBlueString("◉"),
		color.New(color.Bold).Sprintf("Replacing current binary..."))

	// On Windows, we need to rename to a temporary location first, as we can't replace the running file
	// For Unix systems, we can directly replace the file as the inode is still in use by the current process
	backupFile := currentExe + ".backup"

	// Backup current executable first
	err = os.Rename(currentExe, backupFile)
	if err != nil {
		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error backing up current executable"),
			err)
		return
	}

	// Move new executable to the original location
	err = os.Rename(tempFile, currentExe)
	if err != nil {
		// Try to restore backup as the replacement failed
		restoreErr := os.Rename(backupFile, currentExe)
		if restoreErr != nil {
			fmt.Printf("  %s %s\n",
				color.New(color.FgRed, color.Bold).Sprint("❌"),
				color.New(color.Bold).Sprint("Critical error: Failed to replace executable AND restore backup"))
			fmt.Printf("    Original binary located at: %s\n", color.CyanString(backupFile))
			fmt.Printf("    Downloaded binary located at: %s\n", color.CyanString(tempFile))
			return
		}

		fmt.Printf("  %s %s: %s\n",
			color.New(color.FgRed, color.Bold).Sprint("❌"),
			color.New(color.Bold).Sprint("Error replacing executable"),
			err)
		return
	}

	// Remove backup file once successful
	os.Remove(backupFile)

	fmt.Printf("  %s %s\n",
		color.New(color.FgGreen, color.Bold).Sprint("✓"),
		color.New(color.Bold).Sprint("Successfully updated noidea!"))
	fmt.Printf("  %s\n\n",
		color.HiBlackString("Restart any running sessions to use the new version."))
}

// findAppropriateAsset determines which asset to download based on the current OS/architecture
func findAppropriateAsset(release map[string]interface{}) (string, error) {
	assets, ok := release["assets"].([]interface{})
	if !ok || len(assets) == 0 {
		return "", fmt.Errorf("no assets found in release")
	}

	// Determine current OS and architecture
	osName := strings.ToLower(os.Getenv("GOOS"))
	if osName == "" {
		osName = strings.ToLower(runtime.GOOS)
	}

	arch := strings.ToLower(os.Getenv("GOARCH"))
	if arch == "" {
		arch = strings.ToLower(runtime.GOARCH)
	}

	// Look for asset that matches our platform
	var downloadURL string
	for _, asset := range assets {
		assetMap, ok := asset.(map[string]interface{})
		if !ok {
			continue
		}

		name, ok := assetMap["name"].(string)
		if !ok {
			continue
		}

		name = strings.ToLower(name)
		if strings.Contains(name, osName) && strings.Contains(name, arch) {
			browserURL, ok := assetMap["browser_download_url"].(string)
			if ok && browserURL != "" {
				downloadURL = browserURL
				break
			}
		}
	}

	if downloadURL == "" {
		return "", fmt.Errorf("no suitable binary found for %s/%s", osName, arch)
	}

	return downloadURL, nil
}

// downloadBinary downloads the file at url to a temporary file and returns the path
func downloadBinary(url string) (string, error) {
	// Create temporary file
	tempFile, err := os.CreateTemp("", "noidea-update-*.tmp")
	if err != nil {
		return "", fmt.Errorf("failed to create temp file: %w", err)
	}
	defer tempFile.Close()

	// Create HTTP client with timeout
	client := &http.Client{
		Timeout: 5 * time.Minute,
	}

	// Create request
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	// Add user agent
	req.Header.Set("User-Agent", "noidea-updater/"+Version)

	// Download the file
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to download file: %w", err)
	}
	defer resp.Body.Close()

	// Check if request was successful
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("failed to download file, status: %s", resp.Status)
	}

	// Write to temp file
	_, err = io.Copy(tempFile, resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to write temp file: %w", err)
	}

	return tempFile.Name(), nil
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

// updateViaPackageManager shows instructions for updating via package managers
func updateViaPackageManager() {
	fmt.Printf("  %s %s\n",
		color.HiYellowString("◉"),
		color.New(color.Bold).Sprintf("Please update using your package manager:"))

	if _, err := exec.LookPath("apt"); err == nil {
		fmt.Printf("    %s\n\n", color.CyanString("sudo apt update && sudo apt upgrade noidea"))
	} else if _, err := exec.LookPath("yum"); err == nil {
		fmt.Printf("    %s\n\n", color.CyanString("sudo yum update noidea"))
	} else if _, err := exec.LookPath("brew"); err == nil {
		fmt.Printf("    %s\n\n", color.CyanString("brew upgrade noidea"))
	} else {
		fmt.Printf("    %s\n\n", color.HiBlackString("Please use your system's package manager to update"))
	}
}
