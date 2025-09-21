.PHONY: build install uninstall clean lint test release format lint-tools fmt tidy lint-ci pre-commit project-lint script-lint setup-hooks

# Binary name
BINARY=noidea

# Version information
VERSION=$(shell git describe --tags 2>/dev/null || echo "dev")
COMMIT=$(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build with version info
LDFLAGS=-ldflags "-X github.com/AccursedGalaxy/noidea/cmd.Version=$(VERSION) -X github.com/AccursedGalaxy/noidea/cmd.BuildDate=$(BUILD_DATE) -X github.com/AccursedGalaxy/noidea/cmd.Commit=$(COMMIT)"

# Installation paths
PREFIX?=/usr/local
BINDIR?=$(PREFIX)/bin

# Cross-compilation targets
PLATFORMS=darwin/amd64 darwin/arm64 linux/amd64 linux/arm64 windows/amd64

# Determine the real user (in case of sudo)
REAL_USER?=$(shell echo $${SUDO_USER:-$$USER})
REAL_HOME?=$(shell eval echo ~$(REAL_USER))

# Find Go
GO?=$(shell command -v go 2>/dev/null || \
       command -v /usr/local/go/bin/go 2>/dev/null || \
	   command -v /usr/bin/go 2>/dev/null || \
	   command -v $(REAL_HOME)/go/bin/go 2>/dev/null || \
	   echo "go")

# Add a configurable install location with sensible defaults
INSTALL_DIR ?= $(shell if test -d "$(HOME)/bin"; then echo "$(HOME)/bin"; else echo "/usr/local/bin"; fi)

# Default: build the binary
build:
	@echo "Building $(BINARY) version $(VERSION) (commit: $(COMMIT))..."
	@if ! $(GO) version >/dev/null 2>&1; then \
		echo "Error: Go not found. Please install Go or specify GO=/path/to/go"; \
		exit 1; \
	fi
	$(GO) build $(LDFLAGS) -o $(BINARY)
	@echo "✅ Build complete: $(BINARY)"

# Install binary and set up global config directory
install: build
	@echo "Installing $(BINARY) to $(INSTALL_DIR)..."
	mkdir -p $(INSTALL_DIR)
	cp $(BINARY) $(INSTALL_DIR)/
	@echo "Setting up configuration directory..."
	mkdir -p $(REAL_HOME)/.noidea
	@# Create default config.json file if it doesn't exist
	@if [ ! -f "$(REAL_HOME)/.noidea/config.json" ]; then \
		echo "Creating default config.json file..."; \
		echo '{"llm":{"enabled":false,"provider":"xai","api_key":"","model":"grok-4-fast-reasoning","temperature":0.7},"moai":{"use_lint":false,"faces_mode":"random","personality":"snarky_reviewer","personality_file":"$(REAL_HOME)/.noidea/personalities.json"}}' > $(REAL_HOME)/.noidea/config.json; \
		echo "⚠️  No API key is set. Edit $(REAL_HOME)/.noidea/config.json to add your API key."; \
		echo "   Without an API key, AI-powered features like commit message suggestions will use local fallback mode."; \
	fi
	@# Fix ownership if running as root
	@if [ $$(id -u) -eq 0 ] && [ -n "$(SUDO_USER)" ]; then \
		chown -R $(SUDO_USER) $(REAL_HOME)/.noidea; \
	fi
	@echo "✅ Installation complete."
	@echo "Run 'noidea init' in any repository to set up git hooks."
	@echo "Run 'noidea config --init' for interactive configuration setup."

# Create release binaries for multiple platforms
release:
	@echo "Building release binaries for:"
	@mkdir -p dist
	@rm -f dist/*
	@$(foreach platform,$(PLATFORMS),\
		echo "  - $(platform)"; \
		export GOOS=$$(echo $(platform) | cut -d/ -f1); \
		export GOARCH=$$(echo $(platform) | cut -d/ -f2); \
		export OUTPUT=dist/$(BINARY)_$(VERSION)_$${GOOS}_$${GOARCH}; \
		if [ "$${GOOS}" = "windows" ]; then export OUTPUT=$${OUTPUT}.exe; fi; \
		$(GO) build $(LDFLAGS) -o $${OUTPUT}; \
	)
	@echo "✅ Release builds complete. See dist/ directory."
	@echo "Creating checksums file..."
	@cd dist && sha256sum * > checksums-$(VERSION).txt
	@echo "✅ Checksums file created."

# Install dependencies for development
deps:
	$(GO) get -v ./...
	$(GO) get -v github.com/zalando/go-keyring

# Run tests
test:
	@echo "Running tests..."
	$(GO) test -v ./...
	@echo "✅ Tests complete."

# Check if required linting tools are installed and install them if missing
lint-tools:
	@echo "Checking linting tools..."
	@if ! command -v golangci-lint >/dev/null 2>&1; then \
		echo "Installing golangci-lint..."; \
		curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $$(go env GOPATH)/bin v1.55.2; \
	fi
	@if ! command -v goimports >/dev/null 2>&1; then \
		echo "Installing goimports..."; \
		$(GO) install golang.org/x/tools/cmd/goimports@latest; \
	fi
	@echo "✅ Linting tools ready."

# Run comprehensive linting with golangci-lint
lint: lint-tools tidy
	@echo "Running linters on project files only..."
	@bash ./scripts/lint.sh
	@echo "✅ Lint complete."

# Project-only linting (excludes external dependencies)
project-lint: lint

# Script-based linting (more reliable approach)
script-lint: lint

# Format all Go code
fmt: lint-tools
	@echo "Formatting code..."
	@gofmt -w .
	@if command -v goimports >/dev/null 2>&1; then \
		echo "Organizing imports..."; \
		goimports -w -local github.com/AccursedGalaxy/noidea . ; \
	else \
		echo "Installing goimports..."; \
		$(GO) install golang.org/x/tools/cmd/goimports@latest; \
		goimports -w -local github.com/AccursedGalaxy/noidea . ; \
	fi
	@echo "✅ Formatting complete."

# Clean up go.mod and go.sum
tidy:
	@echo "Tidying dependencies..."
	@$(GO) mod tidy
	@echo "✅ Dependencies tidied."

# Format the entire codebase
format: fmt tidy
	@echo "✅ Code formatted and dependencies tidied."

# Run pre-commit checks (useful for git hooks)
pre-commit: tidy format lint
	@echo "Running tests..."
	@$(GO) test -short ./...
	@echo "✅ Pre-commit checks passed."

# Uninstall the binary
uninstall:
	@echo "Uninstalling $(BINARY)..."
	rm -f $(BINDIR)/$(BINARY)
	@echo "✅ Uninstallation complete."

# Clean built binaries and artifacts
clean:
	@echo "Cleaning..."
	rm -f $(BINARY)
	rm -rf dist/
	@echo "✅ Clean complete."

# Setup git hooks
setup-hooks:
	@echo "Setting up git hooks..."
	@./scripts/setup-hooks.sh
	@echo "✅ Git hooks setup complete."

# Show help
help:
	@echo "noidea Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make build      - Build noidea binary"
	@echo "  make install    - Install noidea to $(BINDIR)"
	@echo "  make uninstall  - Remove noidea from $(BINDIR)"
	@echo "  make release    - Build binaries for all platforms"
	@echo "  make lint       - Run linters on project files only"
	@echo "  make fmt        - Format Go code with goimports"
	@echo "  make tidy       - Clean up go.mod and go.sum"
	@echo "  make format     - Format code and tidy dependencies"
	@echo "  make pre-commit - Run all pre-commit checks (format, lint, test)"
	@echo "  make setup-hooks - Set up git hooks for automatic linting"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Remove built binaries"
	@echo "  make deps       - Install dependencies"
	@echo ""
	@echo "Options:"
	@echo "  PREFIX=<path>   - Set installation prefix (default: /usr/local)"
	@echo "  GO=<path>       - Path to Go executable (default: auto-detected)" 