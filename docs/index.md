---
hide:
  - navigation
---

<div class="hero">
  <div class="hero-content">
    <h1><span class="animated-emoji">🧠</span> NoIdea</h1>
    <p>Git Assistant with AI Powers & Sassy Feedback</p>
    <div class="hero-buttons">
      <a href="#installation" class="md-button md-button--primary">Get Started</a>
      <a href="https://github.com/AccursedGalaxy/noidea" class="md-button">GitHub</a>
    </div>
  </div>
</div>

<div class="content-section">
  <h2 id="what-is-noidea">🗿 What is NoIdea?</h2>

  <p>NoIdea is a Git companion that makes your commits better and funnier:</p>

  <ul>
    <li><span class="highlight-text">Get smart commit messages</span> based on your changes</li>
    <li><span class="highlight-text">Receive sassy feedback</span> from a judgmental Moai after each commit</li>
    <li><span class="highlight-text">Analyze your Git history</span> for insights and patterns</li>
  </ul>
</div>

<div class="grid cards" markdown>

- :fontawesome-brands-git-alt: __Smart Commit Messages__

    Get AI-powered commit message suggestions that accurately describe your changes, making your commit history more professional and useful

    [:octicons-arrow-right-24: Learn more](user-guide/features/api-key-management.md)

- :material-message-text: __Sassy Feedback__

    Receive witty, personalized feedback from our judgmental Moai after each commit, with multiple AI personalities to choose from

    [:octicons-arrow-right-24: Features](#features)

- :material-chart-timeline: __Insights & Analysis__

    Track coding patterns, analyze commit quality, and get weekly summaries of your Git activity

    [:octicons-arrow-right-24: Commands](#commands)

- :fontawesome-brands-github: __GitHub Integration__

    Generate AI-enhanced release notes, manage releases, and integrate with GitHub Actions workflows

    [:octicons-arrow-right-24: GitHub Features](#github-integration)

</div>

<div class="content-section">
  <h2 id="installation">⚡ Installation</h2>

  <div class="terminal">
  ```bash
  # Clone and install
  git clone https://github.com/AccursedGalaxy/noidea.git
  cd noidea
  ./install.sh
  ```
  </div>

  <h3>Repository Setup</h3>

  <p>After installation, you need to set up NoIdea in your Git repository:</p>

  <div class="terminal">
  ```bash
  # Navigate to your repository
  cd /path/to/your/repo

  # Initialize NoIdea
  noidea init

  # Enable auto commit suggestions (optional)
  git config noidea.suggest true
  ```
  </div>

  <div class="admonition tip">
    <p class="admonition-title">Pro Tip</p>
    <p>Use <code>noidea config --init</code> to set up your configuration interactively!</p>
  </div>
</div>

<div class="content-section">
  <h2 id="features">✨ Core Features</h2>

  <h3>AI-powered Commit Suggestions</h3>

  <p>When you're ready to commit, NoIdea analyzes your changes and suggests professional commit messages:</p>

  <div class="terminal">
  ```
  ───────────────────────────────────────────────────
  🧠 Analyzing staged changes and 10 recent commits
  Generating professional commit message suggestion...
  ───────────────────────────────────────────────────
  ✨ Suggested commit message:
  feat(user-auth): implement password reset functionality with email verification
  ───────────────────────────────────────────────────
  ```
  </div>

  <h3>Post-commit Feedback</h3>

  <p>After each commit, the Moai will judge your work with witty commentary:</p>

  <div class="terminal">
  ```
  ───────────────────────────────────────────────────
  🗿  (ಠ_ಠ) Your commit message was 'fix final final pls real'
  "You've entered the 2AM hotfix arc. A legendary time."
  ───────────────────────────────────────────────────
  ```
  </div>

  <h3>Weekly Summaries & Git Insights</h3>

  <p>Track your coding patterns and get insights about your work habits with detailed summaries:</p>

  <div class="terminal">
  ```bash
  # Generate a summary of the last 30 days
  noidea summary --days 30
  
  # Include AI insights
  noidea summary --ai
  ```
  </div>

  <h3>AI Personalities</h3>

  <p>NoIdea offers several AI personalities for feedback:</p>

  <div class="personalities-grid">
    <div class="personality">
      <h4>Snarky Code Reviewer</h4>
      <p>Witty, sarcastic feedback that doesn't hold back</p>
    </div>
    <div class="personality">
      <h4>Supportive Mentor</h4>
      <p>Encouraging, positive feedback to keep you motivated</p>
    </div>
    <div class="personality">
      <h4>Git Expert</h4>
      <p>Technical, professional feedback focused on best practices</p>
    </div>
    <div class="personality">
      <h4>Motivational Speaker</h4>
      <p>Energetic enthusiasm to pump you up</p>
    </div>
  </div>

  <p>You can create your own personality easily via our configuration system.</p>
</div>

<div class="content-section">
  <h2 id="github-integration">🚀 GitHub Integration</h2>

  <p>NoIdea provides seamless GitHub integration for managing releases and generating enhanced release notes:</p>

  <h3>Authentication & Setup</h3>

  <div class="terminal">
  ```bash
  # Authenticate with GitHub
  noidea github auth
  
  # Install GitHub hooks (optional)
  noidea github hook-install
  ```
  </div>

  <h3>Enhanced Release Notes</h3>

  <p>Generate AI-powered release notes that enhance GitHub's standard format:</p>

  <div class="terminal">
  ```bash
  # Generate notes for the latest tag
  noidea github release notes
  
  # Wait for GitHub Actions workflows to complete before generating
  noidea github release notes --wait-for-workflows
  ```
  </div>
  
  <div class="admonition tip">
    <p class="admonition-title">Workflow Awareness</p>
    <p>The <code>--wait-for-workflows</code> flag makes NoIdea monitor GitHub Actions status and automatically generate notes once workflows complete, preserving GitHub's generated content while enhancing it with AI.</p>
  </div>
</div>

<div class="content-section">
  <h2 id="commands">🔧 Commands Reference</h2>

  <table>
    <thead>
      <tr>
        <th>Command</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>noidea init</code></td>
        <td>Set up Git hooks in your repository</td>
      </tr>
      <tr>
        <td><code>noidea suggest</code></td>
        <td>Get commit message suggestions</td>
      </tr>
      <tr>
        <td><code>noidea suggest -i</code></td>
        <td>Interactive mode to approve/reject suggestions</td>
      </tr>
      <tr>
        <td><code>noidea suggest -f</code></td>
        <td>Use full diff analysis for more detailed suggestions</td>
      </tr>
      <tr>
        <td><code>noidea moai</code></td>
        <td>Display Moai feedback for the last commit</td>
      </tr>
      <tr>
        <td><code>noidea moai --ai</code></td>
        <td>Use AI-powered feedback analysis</td>
      </tr>
      <tr>
        <td><code>noidea moai --personality supportive_mentor</code></td>
        <td>Use a specific AI personality</td>
      </tr>
      <tr>
        <td><code>noidea moai --list-personalities</code></td>
        <td>List all available personalities</td>
      </tr>
      <tr>
        <td><code>noidea summary [--days 30]</code></td>
        <td>Generate summary of recent Git activity</td>
      </tr>
      <tr>
        <td><code>noidea summary --show-commits</code></td>
        <td>Include detailed commit history in summary</td>
      </tr>
      <tr>
        <td><code>noidea summary --export markdown</code></td>
        <td>Export summary in markdown format</td>
      </tr>
      <tr>
        <td><code>noidea config</code></td>
        <td>Configure noidea</td>
      </tr>
      <tr>
        <td><code>noidea config --init</code></td>
        <td>Interactive configuration setup</td>
      </tr>
      <tr>
        <td><code>noidea config apikey</code></td>
        <td>Set up your API key securely</td>
      </tr>
      <tr>
        <td><code>noidea config apikey-status</code></td>
        <td>Check your API key validity</td>
      </tr>
      <tr>
        <td><code>noidea github auth</code></td>
        <td>Authenticate with GitHub using a Personal Access Token</td>
      </tr>
      <tr>
        <td><code>noidea github status</code></td>
        <td>Check GitHub authentication status</td>
      </tr>
      <tr>
        <td><code>noidea github hook-install</code></td>
        <td>Install GitHub integration Git hooks</td>
      </tr>
      <tr>
        <td><code>noidea github release notes</code></td>
        <td>Generate AI-enhanced release notes</td>
      </tr>
      <tr>
        <td><code>noidea github release notes --wait-for-workflows</code></td>
        <td>Wait for GitHub Actions to complete before generating notes</td>
      </tr>
    </tbody>
  </table>
</div>

<div class="content-section">
  <h2 id="configuration">⚙️ Configuration</h2>

  <p>Configure NoIdea to match your workflow:</p>

  <div class="terminal">
  ```bash
  # Configure interactively
  noidea config --init

  # Add your API key (for AI-powered features)
  noidea config apikey
  
  # Check API key validity
  noidea config apikey-status
  ```
  </div>

  <h3>Advanced Configuration</h3>

  <p>For more advanced setup, you can edit your configuration file at <code>~/.noidea/config.toml</code>:</p>

  <div class="terminal">
  ```toml
  [llm]
  enabled = true
  provider = "xai"
  api_key = ""
  model = "grok-4-fast-reasoning"
  temperature = 0.7

  [moai]
  use_lint = false
  faces_mode = "random"
  personality = "snarky_reviewer"
  personality_file = "~/.noidea/personalities.toml"
  ```
  </div>
</div>

<div class="content-section">
  <h2 id="security">🔒 Security & Privacy</h2>

  <p>NoIdea takes your security seriously:</p>

  <ul>
    <li>API keys are stored securely on your local machine</li>
    <li>No data is sent to our servers - all AI processing happens via your own API keys</li>
    <li>Your commit history and code never leaves your system without your explicit permission</li>
    <li>Legacy .env files are being deprecated in favor of secure storage</li>
  </ul>

  <div class="admonition note">
    <p class="admonition-title">Note</p>
    <p>When using AI features, your code diffs are sent to the AI provider you've configured. Choose a provider you trust.</p>
  </div>
</div>

<div class="content-section">
  <h2 id="why-noidea">🤔 Why NoIdea?</h2>

  <p>Because Git is too serious. Coding is chaos. Let's embrace it.</p>

  <p>This tool won't improve your Git hygiene, but it will make it more entertaining.</p>
</div>

<div class="content-section">
  <h2 id="contribution">🤝 Contribution & Support</h2>

  <p>We welcome contributions from the community! Whether you want to report a bug, suggest a feature, or contribute code, we'd love your help.</p>

  <div class="contribution-links">
    <a href="https://github.com/AccursedGalaxy/noidea/issues/new" class="contribution-link">
      <span class="icon">🐛</span>
      <span class="text">Report a Bug</span>
    </a>
    <a href="https://github.com/AccursedGalaxy/noidea/issues/new" class="contribution-link">
      <span class="icon">💡</span>
      <span class="text">Suggest a Feature</span>
    </a>
    <a href="https://github.com/AccursedGalaxy/noidea/fork" class="contribution-link">
      <span class="icon">🔄</span>
      <span class="text">Fork the Project</span>
    </a>
    <a href="https://github.com/AccursedGalaxy/noidea/pulls" class="contribution-link">
      <span class="icon">🚀</span>
      <span class="text">Submit a PR</span>
    </a>
  </div>
</div>

<div class="content-section">
  <div class="feature-status">
  <h2 id="project-status">📊 Project Status</h2>

  <table>
    <thead>
      <tr>
        <th>Feature</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Moai face after commit</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>AI-based commit feedback</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>Config file support</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>Weekly summaries</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>On-demand commit analysis</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>Commit message suggestions</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>Enhanced terminal output</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>POSIX-compatible hooks</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>Secure API key storage</td>
        <td>✅ Done</td>
      </tr>
      <tr>
        <td>Lint feedback</td>
        <td>🛠️ In progress</td>
      </tr>
      <tr>
        <td>Commit streak insights</td>
        <td>🔜 Coming Soon</td>
      </tr>
    </tbody>
  </table>
  </div>
</div>

<div class="github-card">
  <a href="https://github.com/AccursedGalaxy/noidea" title="Star AccursedGalaxy/noidea on GitHub">
    <img src="https://img.shields.io/github/stars/AccursedGalaxy/noidea?style=social" alt="GitHub stars">
  </a>
  <a href="https://github.com/AccursedGalaxy/noidea/issues">
    <img src="https://img.shields.io/github/issues/AccursedGalaxy/noidea" alt="GitHub issues">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
</div>
