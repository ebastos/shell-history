set shell := ["bash", "-c"]

# Use absolute path to ensure binary matches project location
project_root := invocation_directory()
client_dir := project_root / "client"
backend_dir := project_root / "backend"

# Default command: list available recipes
default:
    @just --list

# --- Testing ---

# Run all tests (backend and client)
test: test-backend test-client

# Run backend tests using pytest
test-backend:
    cd {{backend_dir}} && uv run pytest

# Run Go client tests (unit and BDD)
test-client:
    cd {{client_dir}} && go test ./...

# --- CLI Management ---

# Build the Go client locally
build-client:
    cd {{client_dir}} && go build -o shell-history

# Build and install the CLI to ~/bin
install-client: build-client
    mkdir -p ~/bin
    cp {{client_dir}}/shell-history ~/bin/
    @echo "CLI installed to ~/bin/shell-history"

# Uninstall the CLI from ~/bin
uninstall-client:
    rm -f ~/bin/shell-history
    @echo "CLI removed from ~/bin"

# --- Docker Operations ---

# Start backend services in detached mode
up:
    docker compose up -d

# Stop and remove Docker containers
down:
    docker compose down

# Tail Docker logs
logs:
    docker compose logs -f

# Restart Docker services
restart: down up

# List running services
ps:
    docker compose ps

# --- Maintenance ---

# Run pre-commit hooks on all files
lint:
    pre-commit run --all-files

# Clean up build artifacts and caches
clean:
    rm -rf {{client_dir}}/shell-history
    find . -type d -name "__pycache__" -exec rm -rf {} +
    rm -rf .pytest_cache .ruff_cache backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
    @echo "Cleanup complete."

# Update dependencies (Go and Python)
update:
    cd {{client_dir}} && go mod tidy
    cd {{backend_dir}} && uv lock --upgrade
