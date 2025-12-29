# Development Guide

Everything you need to contribute code to Shell History.

## Table of Contents

- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Running Services](#running-services)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Development Workflow](#development-workflow)
- [Common Tasks](#common-tasks)

---

## Development Environment

### Prerequisites

- **Python 3.11+** with [uv](https://github.com/astral-sh/uv) package manager
- **Go 1.21+**
- **Docker** and **Docker Compose**

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-username/shell-history.git
cd shell-history

# Install Python dependencies
cd backend
uv sync --extra dev
cd ..

# Install Go dependencies
cd client
go mod download
cd ..

# Install pre-commit hooks
uv run pre-commit install
```

---

## Project Structure

```
shell-history/
├── backend/              # FastAPI server (Python)
│   ├── app/
│   │   ├── routers/      # API and UI endpoints
│   │   ├── services/     # Business logic
│   │   ├── templates/    # HTML/HTMX templates
│   │   ├── static/       # CSS and assets
│   │   ├── models.py     # SQLAlchemy models
│   │   └── schemas.py    # Pydantic schemas
│   └── tests/            # Pytest tests
├── client/               # Go CLI
│   ├── cmd/              # CLI commands
│   ├── internal/         # Core logic
│   └── integration/      # Shell integration scripts
├── docs/                 # Documentation
└── plans/                # Design documents
```

---

## Running Services

### Start Everything (Docker Compose)

```bash
docker-compose up -d
```

This starts:
- **API** on http://localhost:3000
- **Meilisearch** on http://localhost:7700
- **MailHog** on http://localhost:8025

### Run Backend Locally (for development)

```bash
# Start dependencies only
docker-compose up -d meilisearch mailhog

# Run backend with hot reload
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### Build Go Client

```bash
cd client
go build -o shell-history main.go
```

---

## Testing

### Python Backend

```bash
cd backend

# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_commands.py

# Run specific test function
uv run pytest tests/test_commands.py::test_create_command

# With coverage
uv run pytest --cov=app --cov-report=term-missing
```

### Go Client

```bash
cd client

# Run all tests
go test ./...

# Verbose output
go test -v ./...

# Run specific package tests
go test -v ./cmd/...
```

### Email Testing with MailHog

When running with Docker Compose, all emails are captured by MailHog:

1. Start services: `docker-compose up -d`
2. View emails at http://localhost:8025
3. Password reset and verification emails appear here
4. Click links directly from MailHog to test flows

---

## Code Quality

### Python Linting & Formatting

```bash
cd backend

# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking
uv run mypy .
```

### Go Linting & Formatting

```bash
cd client

# Vet (find common errors)
go vet ./...

# Format code
go fmt ./...
```

### Pre-commit Hooks

Pre-commit runs automatically on `git commit`. To run manually:

```bash
# Run on staged files
uv run pre-commit run

# Run on all files
uv run pre-commit run --all-files
```

---

## Development Workflow

### Test-Driven Development (TDD)

> [!IMPORTANT]
> All new features MUST follow the Red-Green-Refactor cycle.

1. **RED**: Write a failing test that describes the desired behavior
2. **GREEN**: Write the minimum code to make the test pass
3. **REFACTOR**: Improve code quality while keeping tests green

### Bug Fix Workflow

> [!IMPORTANT]
> Before fixing any bug, create a regression test that reproduces it.

1. Write a failing test that demonstrates the bug
2. Fix the bug (test should now pass)
3. Run full test suite to ensure no regressions

### Pre-Commit Checklist

- [ ] All tests pass: `uv run pytest` (backend), `go test ./...` (client)
- [ ] Linting passes: `uv run ruff check .` (backend), `go vet ./...` (client)
- [ ] Formatting applied: `uv run ruff format .` (backend), `go fmt ./...` (client)
- [ ] Type checking passes: `uv run mypy .` (backend)
- [ ] Documentation updated if needed

---

## Common Tasks

### Adding an API Endpoint

1. Write a failing test in `backend/tests/`
2. Add Pydantic schema in `backend/app/schemas.py`
3. Add route in `backend/app/routers/`
4. Add business logic in `backend/app/services/` if complex
5. Make the test pass
6. Update docs if user-facing

### Adding a CLI Command

1. Write a failing test in `client/cmd/`
2. Create command file in `client/cmd/`
3. Register in `client/cmd/root.go`
4. Make the test pass
5. Update docs if user-facing

### Modifying Database Models

1. Write a failing test
2. Update `backend/app/models.py`
3. Update `backend/app/schemas.py`
4. Update Meilisearch index in `backend/app/services/search.py` if needed
5. Make the test pass

---

## Using the Justfile

Common tasks are available via [just](https://github.com/casey/just):

```bash
# Run backend tests
just test

# Start Docker services
just up

# View logs
just logs

# Build and install CLI
just build-cli
```

See `justfile` for all available commands.

---

**Questions?** See [CONTRIBUTING.md](CONTRIBUTING.md) or [open an issue](https://github.com/your-username/shell-history/issues).
