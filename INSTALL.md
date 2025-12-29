# Installation Guide

Complete installation instructions for Shell History — server, client, and shell integration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Server Setup](#server-setup)
- [Client Installation](#client-installation)
- [Authentication Setup](#authentication-setup)
- [Shell Integration](#shell-integration)
- [Configuration Reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Docker** and **Docker Compose** (for server)
- **Go 1.21+** (for building the CLI client)
- **Bash** or **Zsh** shell

---

## Server Setup

### Option A: Docker Compose (Recommended)

The easiest way to run the server and all dependencies:

```bash
# Clone the repository
git clone https://github.com/your-username/shell-history.git
cd shell-history

# Configure the admin user (required for first startup)
export ADMIN_USERNAME=admin
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=your-secure-password
export SECRET_KEY=your-secret-key-for-sessions

# Start all services
docker-compose up -d
```

**Services available:**

| Service | URL | Description |
|---------|-----|-------------|
| Web UI & API | http://localhost:3000 | Main application |
| API | http://localhost:3000/api/v1 | REST API endpoints |
| Meilisearch | http://localhost:7700 | Search engine admin |
| MailHog | http://localhost:8025 | Email testing (dev only) |

### Option B: Manual Setup

For development or custom deployments:

```bash
# 1. Start Meilisearch
docker run -d -p 7700:7700 getmeili/meilisearch:latest

# 2. Install Python dependencies
cd backend
pip install uv
uv sync

# 3. Run the backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 3000
```

### Production Considerations

> [!IMPORTANT]
> For production deployments:

- Set a strong `SECRET_KEY` environment variable
- Use a proper SMTP server instead of MailHog
- Consider using PostgreSQL instead of SQLite for better concurrency
- Put the application behind a reverse proxy (nginx, Caddy) with TLS
- Set `MEILISEARCH_MASTER_KEY` to secure your search engine

---

## Client Installation

### Building from Source

```bash
cd client
go build -o shell-history main.go
```

### Installing the Binary

Move the binary to a directory in your PATH:

```bash
# Option A: System-wide (requires sudo)
sudo mv shell-history /usr/local/bin/

# Option B: User-local
mkdir -p ~/bin
mv shell-history ~/bin/
# Add to PATH if not already: export PATH="$HOME/bin:$PATH"
```

Verify installation:

```bash
shell-history --help
```

---

## Authentication Setup

### 1. Admin User (Auto-created)

The admin user is automatically created on server startup from environment variables:

```bash
export ADMIN_USERNAME=admin
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=your-secure-password
```

### 2. Create User Accounts

**Option A: Admin Dashboard (Recommended)**

1. Navigate to http://localhost:3000/admin
2. Log in with admin credentials
3. Create new users — API keys are auto-generated

**Option B: API (Admin Only)**

> [!NOTE]
> User creation via API requires admin authentication.

```bash
curl -X POST http://localhost:3000/api/v1/users \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <admin-api-key>" \
  -d '{
    "username": "myuser",
    "email": "myuser@example.com",
    "password": "secure-password",
    "role": "user"
  }'
```

### 3. Get Your API Key

After account creation, get your API key:

1. Log in at http://localhost:3000/login
2. Go to http://localhost:3000/account
3. Create a new API key or view existing ones

> [!TIP]
> Copy your API key immediately — the full key is only shown once!

### 4. Configure the CLI

```bash
# Set your API key
shell-history config set-api-key <your-api-key>

# Verify configuration
shell-history config show

# Test connection
shell-history test
```

### 5. (Optional) Custom Server URL

If your server isn't on localhost:3000:

```bash
shell-history config set-server http://your-server:3000
```

---

## Shell Integration

Add shell integration to capture every command automatically.

### Bash

Add to `~/.bashrc`:

```bash
source /path/to/shell-history/client/integration/bash.sh
```

### Zsh

Add to `~/.zshrc`:

```bash
source /path/to/shell-history/client/integration/zsh.sh
```

After adding, reload your shell:

```bash
exec $SHELL
```

### How It Works

The integration scripts hook into your shell's command execution:

- **Bash**: Uses `PROMPT_COMMAND`
- **Zsh**: Uses `preexec` hook

Commands are captured in the background, so there's no impact on shell responsiveness. If the server is unreachable, commands are buffered locally and synced later.

---

## Configuration Reference

### Client Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HISTORY_CLIENT_URL` | `http://localhost:3000` | Server URL |
| `HISTORY_API_KEY` | (none) | API key for authentication |

Configuration is stored in `~/.config/shell-history/config.json`. Environment variables take precedence over the config file.

### Server Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/history.db` | Database connection |
| `MEILISEARCH_URL` | `http://localhost:7700` | Meilisearch URL |
| `MEILISEARCH_MASTER_KEY` | (none) | Meilisearch auth key |
| `ADMIN_USERNAME` | (none) | Initial admin username |
| `ADMIN_EMAIL` | (none) | Initial admin email |
| `ADMIN_PASSWORD` | (none) | Initial admin password |
| `SECRET_KEY` | `change-me-in-production` | Session signing key |
| `SMTP_HOST` | `localhost` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | (none) | SMTP username |
| `SMTP_PASSWORD` | (none) | SMTP password |
| `SMTP_FROM_EMAIL` | `noreply@example.com` | Sender email |
| `SMTP_USE_TLS` | `true` | Use TLS for SMTP |

### Client-Side Redaction

Redaction rules are configured locally on the client and applied before commands are sent to the server. This keeps sensitive data from ever leaving your machine.

**Configure redaction rules:**

```bash
# List current rules
shell-history redaction list

# Add common redaction patterns
shell-history redaction add --name "AWS Keys" --pattern "AKIA[0-9A-Z]{16}" --replacement "[AWS_KEY]"
shell-history redaction add --name "Passwords" --pattern "--password\s+\S+" --replacement "--password [REDACTED]"
shell-history redaction add --name "Bearer Tokens" --pattern "Bearer\s+[^\s']+" --replacement "Bearer [TOKEN]"
shell-history redaction add --name "API Keys" --pattern "api[_-]?key\s*[=:]\s*[^\s']+" --replacement "api_key=[REDACTED]"

# Remove a rule
shell-history redaction remove "AWS Keys"
```

Rules are stored in `~/.config/shell-history/config.json` and support regex patterns.

**Example config file:**

```json
{
  "server_url": "http://localhost:3000",
  "api_key": "your-api-key",
  "redaction_rules": [
    {"name": "AWS Keys", "pattern": "AKIA[0-9A-Z]{16}", "replacement": "[AWS_KEY]"},
    {"name": "Passwords", "pattern": "--password\\s+\\S+", "replacement": "--password [REDACTED]"}
  ]
}
```

> [!NOTE]
> No redaction is applied by default. Configure rules for any sensitive patterns you want to protect.

---

## Troubleshooting

### "Connection refused" when running CLI commands

- Ensure the server is running: `docker-compose ps`
- Check the server URL: `shell-history config show`
- Verify your API key is set: `shell-history test`

### Commands not being captured

- Verify shell integration is loaded: `type shell_history_capture` (should show a function)
- Check if the CLI is in your PATH: `which shell-history`
- Test manual capture: `shell-history capture "test command"`

### "Unauthorized" errors

- Regenerate your API key from the web UI
- Reconfigure the CLI: `shell-history config set-api-key <new-key>`

### Server won't start

- Check Docker logs: `docker-compose logs api`
- Ensure required env vars are set: `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- Check if ports are available: 3000, 7700, 8025

### Search not returning results

- New commands take a moment to be indexed
- Force a flush: `shell-history flush`
- Check Meilisearch status: http://localhost:7700

---

**Need more help?** [Open an issue](https://github.com/your-username/shell-history/issues) on GitHub.
