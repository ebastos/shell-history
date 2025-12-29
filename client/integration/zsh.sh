#!/bin/zsh
# Shell History - Zsh Integration
# Add this to your ~/.zshrc: source /path/to/zsh.sh

# Configuration
export HISTORY_CLIENT_URL="${HISTORY_CLIENT_URL:-http://localhost:3000}"

# Ensure shell-history is in PATH
if ! command -v shell-history &>/dev/null; then
    # Try common installation paths
    if [[ -x "$HOME/.local/bin/shell-history" ]]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

# Capture history function
_capture_history() {
    local exit_code=$?
    local last_cmd="${1}"

    # Skip empty commands and space-prefixed commands (private)
    if [[ -n "$last_cmd" && ! "$last_cmd" =~ ^[[:space:]] ]]; then
        # Run capture in background to avoid blocking the shell
        (shell-history capture "$last_cmd" --exit-code "$exit_code" --cwd "$PWD" --server "$HISTORY_CLIENT_URL" &) 2>/dev/null
    fi

    # Flush buffer periodically (1% chance)
    if (( RANDOM % 100 == 0 )); then
        (shell-history flush --server "$HISTORY_CLIENT_URL" &) 2>/dev/null
    fi
}

# Use zsh's preexec hook
# Avoid duplicate registration
if [[ ! "${preexec_functions}" == *"_capture_history"* ]]; then
    preexec_functions+=(_capture_history)
fi

# Aliases
alias history-search='shell-history search'
alias history-stats='shell-history stats'
alias history-flush='shell-history flush'

if [[ -o interactive ]]; then
    echo "Shell History integration enabled."
fi
