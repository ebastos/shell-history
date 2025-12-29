# Architecture

System design, data model, and implementation details for Shell History.

## Overview

Shell History is a centralized command history system that captures shell commands from multiple machines and makes them searchable.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Shell Hook     │────▶│   Go Client     │────▶│  FastAPI Server │
│  (bash/zsh)     │     │   (CLI)         │     │  (Python)       │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌──────────────────────────┼──────────────────────────┐
                              │                          │                          │
                              ▼                          ▼                          ▼
                        ┌───────────┐            ┌─────────────┐            ┌───────────────┐
                        │  SQLite   │            │ Meilisearch │            │   HTMX Web    │
                        │ Database  │            │  (Search)   │            │   Interface   │
                        └───────────┘            └─────────────┘            └───────────────┘
```

---

## Components

### Shell Integration

Hooks into shell command execution to capture commands transparently.

- **Bash**: Uses `PROMPT_COMMAND` hook
- **Zsh**: Uses `preexec` hook

Located in: `client/integration/`

### Go Client (CLI)

High-performance command-line tool for:

- Capturing commands from shell hooks
- Searching command history
- Managing configuration
- Buffering commands when offline

Located in: `client/`

**Key features:**
- Local buffer for offline resilience
- Background sync to server
- Session management

### FastAPI Backend

Python web server handling:

- REST API for all operations
- HTMX-based web interface
- User authentication (session + API key)
- Data persistence

Located in: `backend/`

### Meilisearch

Lightning-fast full-text search engine.

- Indexes all commands for instant search
- Filters by user for multi-tenancy
- Typo-tolerant search

### Web Interface

Server-rendered HTMX interface for:

- Searching command history
- Managing account and API keys
- Admin user management

Located in: `backend/app/templates/`

---

## Request Flow

### Command Capture

```
1. User runs command in shell
2. Shell hook detects command completion
3. Hook calls: shell-history capture "command" --exit-code 0
4. CLI buffers command locally (SQLite)
5. CLI syncs to server in background
6. Server stores in database
7. Server indexes in Meilisearch
```

### Command Search

```
1. User: shell-history search "docker"
2. CLI sends GET /api/v1/commands?q=docker
3. Server queries Meilisearch (filtered by user_id)
4. Server returns matching commands
5. CLI displays results
```

---

## Multi-Tenancy

Shell History is a **multi-tenant** system with strict user isolation.

### User Isolation

- Each user only sees their own commands
- Hosts are scoped per user (same hostname can exist for different users)
- All queries automatically filter by `user_id`

### Authentication Methods

| Method | Use Case | How It Works |
|--------|----------|--------------|
| **API Key** | CLI, programmatic access | `X-API-Key` header |
| **Session** | Web interface | Secure HTTP-only cookies |

### API Keys

- Multiple keys per user allowed
- Keys can be revoked individually
- Usage tracked (last used timestamp)
- Created automatically with user account

---

## Data Model

### Command

The core entity storing captured commands.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `command` | Text | The executed command |
| `hostname` | String | Source machine |
| `username` | String | Shell user |
| `cwd` | String | Working directory |
| `exit_code` | Integer | Command exit status |
| `timestamp` | DateTime | Execution time |
| `session_id` | UUID | Terminal session |
| `redacted` | Boolean | Whether sensitive data was masked |
| `user_id` | UUID | Owner (for multi-tenancy) |

### Host

Tracks machines that have sent commands.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `hostname` | String | Machine hostname |
| `ip_address` | String | IP address (optional) |
| `os_type` | String | Operating system |
| `is_active` | Boolean | Active status |
| `last_seen` | DateTime | Last activity |
| `user_id` | UUID | Owner (for multi-tenancy) |

### User

User accounts for authentication and isolation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `username` | String | Unique username |
| `email` | String | Email address |
| `role` | String | `user`, `admin`, or `readonly` |
| `password_hash` | String | Bcrypt hash |
| `is_active` | Boolean | Account status |
| `created_at` | DateTime | Creation time |

### ApiKey

API keys for programmatic authentication.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Owner |
| `key` | String | The API key value |
| `name` | String | User-friendly label |
| `created_at` | DateTime | Creation time |
| `last_used_at` | DateTime | Last usage |
| `is_active` | Boolean | Whether key is valid |

### PasswordResetToken

Tokens for password reset flow.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | User requesting reset |
| `token` | String | Secure token |
| `expires_at` | DateTime | Expiry (24 hours) |
| `used_at` | DateTime | When used |

### EmailVerificationToken

Tokens for email change verification.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | User changing email |
| `new_email` | String | New email to verify |
| `token` | String | Secure token |
| `expires_at` | DateTime | Expiry (24 hours) |
| `used_at` | DateTime | When used |

---

## Security

### Sensitive Data Redaction

Commands are automatically scanned for sensitive data before storage:

| Pattern | Example | Replacement |
|---------|---------|-------------|
| AWS Access Keys | `AKIAIOSFODNN7EXAMPLE` | `[REDACTED]` |
| Password arguments | `--password secret123` | `--password [REDACTED]` |
| API keys | `api_key=abc123` | `api_key=[REDACTED]` |
| Bearer tokens | `Bearer eyJ...` | `Bearer [REDACTED]` |
| Private keys | `-----BEGIN ... KEY-----` | `[REDACTED]` |

### Authentication

- **Passwords**: Bcrypt hashed with salt
- **Sessions**: Signed cookies with `SECRET_KEY`
- **API Keys**: Stored in plaintext (consider hashing for production)

### Security Recommendations

> [!CAUTION]
> For production deployments:

- Use a strong, random `SECRET_KEY`
- Enable TLS (HTTPS) via reverse proxy
- Set `MEILISEARCH_MASTER_KEY`
- Consider hashing API keys
- Use PostgreSQL for better concurrency

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Pydantic |
| Frontend | HTMX, Jinja2 templates, vanilla CSS |
| Client | Go 1.21+, Cobra CLI framework |
| Database | SQLite (PostgreSQL compatible) |
| Search | Meilisearch |
| Email | SMTP (MailHog for development) |
