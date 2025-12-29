# AGENTS.md

> Guidelines for AI coding assistants working on this codebase.

## Project Overview

**Shell History** is a centralized shell command history system that captures, stores, and enables searching of shell commands across multiple hosts.

**Architecture**: Shell Integration → Go Client → FastAPI Backend → SQLite + Meilisearch → HTMX Web UI

**Stack**:
- **Backend**: FastAPI (Python 3.11+) with SQLAlchemy, Pydantic, HTMX/Jinja2
- **Client**: Go CLI (Cobra framework)
- **Search**: Meilisearch
- **Storage**: SQLite

## Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | User-facing intro and quick start |
| [INSTALL.md](INSTALL.md) | Complete installation guide |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Developer setup and workflows |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [docs/API.md](docs/API.md) | REST API reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data model |

---

## Development Workflow

### Test-Driven Development (TDD) - REQUIRED

> [!IMPORTANT]
> **All new features MUST follow the Red-Green-Refactor cycle.**

1. **RED**: Write a failing test that describes the desired behavior
2. **GREEN**: Write the minimum code to make the test pass
3. **REFACTOR**: Improve code quality while keeping tests green

**Workflow for new features:**
```bash
# 1. Write failing test
cd backend
uv run pytest tests/test_new_feature.py::test_feature -v

# 2. Implement feature (test should pass)
# 3. Refactor if needed
# 4. Ensure all tests pass
uv run pytest
```

### Bug Fix Workflow - REQUIRED

> [!IMPORTANT]
> **Before fixing any reported bug, you MUST create a regression test that reproduces the bug.**

1. **Reproduce**: Write a failing test that demonstrates the bug
2. **Fix**: Implement the fix (test should now pass)
3. **Verify**: Run full test suite to ensure no regressions

**Workflow for bug fixes:**
```bash
# 1. Write regression test (should fail)
cd backend
uv run pytest tests/test_bug.py::test_bug_reproduction -v

# 2. Fix the bug (test should pass)
# 3. Run full test suite
uv run pytest
```

### Documentation Updates - REQUIRED

> [!IMPORTANT]
> **All code changes MUST be accompanied by documentation updates.**

When modifying code, update:
- **README.md**: If user-facing features, API changes, or setup instructions change
- **CHANGELOG.md**: If it exists, document all user-visible changes
- **This file (AGENTS.md)**: If workflows, conventions, or project structure change
- **Code comments/docstrings**: For public APIs and complex logic

---

## Dev Environment

### Package Manager: uv

**Do not use pip or poetry.** This project uses `uv` for Python dependency management.

```bash
# Install dependencies
uv sync --extra dev

# Add dependency
cd backend && uv add <package>

# Run commands
uv run pytest
uv run ruff check .
```

### Running Services

```bash
# Start all services (Meilisearch, MailHog, Backend)
docker-compose up -d

# Or start individual services
docker-compose up -d meilisearch mailhog

# Run backend locally (port 8000)
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Build Go client
cd client && go build -o shell-history main.go
```

**Development Email Testing:**
- MailHog UI: http://localhost:8025 (view captured emails)
- All emails (password reset, email verification) are captured automatically
- No SMTP configuration needed for development

---

## Testing

### Python Backend

```bash
cd backend
uv run pytest                              # All tests
uv run pytest -v                           # Verbose
uv run pytest -k "<test name>"             # Specific test
uv run pytest tests/test_file.py::test_fn  # Specific function
```

### Go Client

```bash
cd client
go test ./...                              # All tests
go test -v ./cmd/...                       # Verbose, specific package
```

> [!IMPORTANT]
> All tests must pass before committing. Run `uv run pytest` in backend before any PR.

---

## Code Quality

### Python (ruff + mypy)

```bash
cd backend
uv run ruff check .                        # Lint
uv run ruff check --fix .                  # Auto-fix
uv run ruff format .                       # Format
uv run mypy .                              # Type check
```

### Go

```bash
cd client
go vet ./...
go fmt ./...
```

---

## Code Conventions

### Python
- **Type hints**: Required on all function signatures
- **Docstrings**: Google-style for public functions
- **Imports**: Absolute imports, sorted by ruff
- **Async**: Use async/await for API endpoints

### Go
- **Error handling**: Return errors, don't panic
- **Naming**: camelCase (unexported), PascalCase (exported)

### Frontend
- **No build step**: HTMX + Jinja2 templates only
- **Templates**: `backend/app/templates/`
- **Static files**: `backend/app/static/`

---

## API Endpoints

Base URL: `http://localhost:3000/api/v1`

> [!IMPORTANT]
> All endpoints require `X-API-Key` header (except `/health`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/commands` | Ingest command |
| GET | `/commands` | Search/list commands |
| GET/DELETE | `/commands/{id}` | Get/delete command |
| GET/POST | `/hosts` | List/create hosts |
| GET/PUT | `/hosts/{id}` | Get/update host |
| GET/POST | `/users` | List/create users |
| GET | `/users/me` | Current user info |
| POST | `/users/me/api-key/regenerate` | Regenerate API key |
| GET | `/stats` | Statistics |

**Admin UI** (session-based auth): `/admin`, `/admin/login`, `/admin/users/*`

---

## Environment Variables

### Server
- `DATABASE_URL`: SQLite path (default: `sqlite:///./data/history.db`)
- `MEILISEARCH_URL`: Meilisearch URL (default: `http://localhost:7700`)
- `MEILISEARCH_MASTER_KEY`: Meilisearch auth key
- `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`: Initial admin user
- `SECRET_KEY`: Session signing key (required for admin interface)
- `SMTP_HOST`: SMTP server hostname (default: `localhost`, `mailhog` in Docker)
- `SMTP_PORT`: SMTP server port (default: `587`, `1025` for MailHog)
- `SMTP_USER`: SMTP username (optional, required for authenticated SMTP)
- `SMTP_PASSWORD`: SMTP password (optional, required for authenticated SMTP)
- `SMTP_FROM_EMAIL`: Sender email address (default: `noreply@example.com`)
- `SMTP_USE_TLS`: Use TLS for SMTP (default: `true`, `false` for MailHog)

> [!NOTE]
> When using Docker Compose, MailHog is automatically configured. For production, set real SMTP credentials.

### Client
- `HISTORY_CLIENT_URL`: Server URL (default: `http://localhost:3000`)
- `HISTORY_API_KEY`: API key for authentication

---

## Common Tasks

### Adding API Endpoint
1. Write failing test (TDD)
2. Add Pydantic schema in `backend/app/schemas.py`
3. Add route in `backend/app/routers/`
4. Add business logic in `backend/app/services/`
5. Make test pass, refactor
6. Update README.md if user-facing

### Adding CLI Command
1. Write failing test (TDD)
2. Create file in `client/cmd/`
3. Register in `client/cmd/root.go`
4. Make test pass, refactor
5. Update README.md if user-facing

### Modifying Database Models
1. Write failing test (TDD)
2. Update `backend/app/models.py`
3. Update `backend/app/schemas.py`
4. Update Meilisearch index in `backend/app/services/search.py` if needed
5. Make test pass, refactor

---

## Pre-Commit Checklist

- [ ] All tests pass: `uv run pytest` (backend), `go test ./...` (client)
- [ ] Linting passes: `uv run ruff check .` (backend), `go vet ./...` (client)
- [ ] Formatting applied: `uv run ruff format .` (backend), `go fmt ./...` (client)
- [ ] Type checking passes: `uv run mypy .` (backend)
- [ ] Documentation updated: README.md, CHANGELOG.md (if exists), AGENTS.md (if needed)
- [ ] Regression tests added for bug fixes
- [ ] TDD cycle followed for new features

---

## Constraints and Gotchas

> [!CAUTION]
> - **Multi-Tenancy**: All endpoints require API key auth. Each user only sees their own data.
> - **Sensitive Data**: Redaction is client-side with user-configurable rules. Don't log raw command input on the server.
> - **Meilisearch Sync**: Commands indexed asynchronously. Search filtered by user_id.
> - **SQLite Locking**: Only one write at a time. Use proper async patterns.
> - **Host Isolation**: Hosts scoped per user. Same hostname can exist for different users.
> - **API Keys**: Stored in plaintext. Consider hashing for production.
> - **Admin Interface**: Password-based auth with session cookies. Initial admin from env vars. Set `SECRET_KEY` securely in production.

> [!NOTE]
> Frontend migrated from Vue.js to HTMX in Dec 2025. Ignore references to `web/` directory or npm/Vite build steps.
