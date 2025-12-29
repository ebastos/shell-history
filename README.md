# 🐚 Shell History

> **Never lose a command again.** Capture, search, and sync your shell history across all your machines.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go)](https://golang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)

---

## ✨ Why Shell History?

Ever spent 10 minutes trying to remember that complex `docker` command you ran last week? Or that clever `awk` one-liner from months ago on a different machine?

**Shell History** solves this by:

- 🔍 **Instant full-text search** across your entire command history
- 🌐 **Unified history** from all your machines in one place
- 🔒 **Client-side redaction** of passwords, API keys, and secrets (user-configurable)
- ⚡ **Zero friction** — commands captured transparently in the background
- 🛡️ **Multi-tenant** — your data stays yours with user isolation


---

## 🚀 Quick Start

Get up and running in 3 steps:

### 1. Start the Server

```bash
git clone https://github.com/your-username/shell-history.git
cd shell-history
docker-compose up -d
```

### 2. Install the CLI

```bash
cd client
go build -o shell-history main.go
sudo mv shell-history /usr/local/bin/
```

### 3. Connect & Capture

```bash
# Configure your API key (get it from http://localhost:3000/account after login)
shell-history config set-api-key <your-api-key>

# Add to your shell (Zsh example)
echo 'source /path/to/shell-history/client/integration/zsh.sh' >> ~/.zshrc
source ~/.zshrc

# That's it! Every command is now captured.
```

**Search your history:**
```bash
shell-history search "docker-compose"
```

👉 **Need more details?** See the [Installation Guide](INSTALL.md) for complete setup instructions.

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| **Full-Text Search** | Search through thousands of commands instantly with Meilisearch |
| **Multi-Host Support** | Commands from all your machines in one searchable place |
| **Web Interface** | Beautiful HTMX-powered UI for browsing and searching history |
| **Offline Resilience** | Local buffering ensures no commands are lost when offline |
| **Sensitive Data Redaction** | Client-side redaction with user-configurable regex patterns |
| **Multi-Tenant** | User-based isolation — your data stays private |
| **API Access** | Full REST API for integrating with other tools |

---

## 📚 Documentation

| Guide | Description |
|-------|-------------|
| [**Installation Guide**](INSTALL.md) | Complete setup for server, client, and shell integration |
| [**API Reference**](docs/API.md) | REST API endpoints with examples |
| [**Architecture**](docs/ARCHITECTURE.md) | System design, data model, and multi-tenancy |
| [**Development Guide**](DEVELOPMENT.md) | Set up your dev environment and run tests |
| [**Contributing**](CONTRIBUTING.md) | How to contribute to Shell History |

---

## 🧰 CLI Commands

```bash
# Search commands
shell-history search "git commit"
shell-history search "npm" --hostname my-laptop --limit 20

# View statistics
shell-history stats

# Configuration
shell-history config show
shell-history config set-api-key <key>
shell-history config set-server <url>

# Redaction rules (client-side)
shell-history redaction list                                    # Show configured rules
shell-history redaction add --name "AWS Keys" --pattern "AKIA[0-9A-Z]{16}" --replacement "[AWS_KEY]"
shell-history redaction remove "AWS Keys"

# Utilities
shell-history flush    # Force flush buffered commands
shell-history test     # Test server connection
```

---

## 🤝 Contributing

We welcome contributions! Whether it's:

- 🐛 Reporting bugs
- 💡 Suggesting features
- 📖 Improving documentation
- 🔧 Submitting pull requests

See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Made with ❤️ for developers who value their command history</strong>
</p>
