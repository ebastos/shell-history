#!/bin/bash
# Shell History - Bash Integration
# Add this to your ~/.bashrc: source /path/to/bash.sh

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
    local last_cmd

    # Get the last command from history
    last_cmd=$(history 1 | sed 's/^[ ]*[0-9]*[ ]*//')

    # Skip empty commands and space-prefixed commands (private)
    if [[ -n "$last_cmd" && ! "$last_cmd" =~ ^[[:space:]] ]]; then
        # Run capture in background to avoid blocking the shell
        (shell-history capture "$last_cmd" --exit-code "$exit_code" --cwd "$PWD" --server "$HISTORY_CLIENT_URL" &) 2>/dev/null
    fi

    # Flush buffer periodically (1% chance)
    if (( RANDOM % 100 == 0 )); then
        (shell-history flush --server "$HISTORY_CLIENT_URL" &) 2>/dev/null
    fi

    # Call original PROMPT_COMMAND if it was set
    if [[ -n "$_ORIGINAL_PROMPT_COMMAND" ]]; then
        eval "$_ORIGINAL_PROMPT_COMMAND"
    fi
}

# Ensure we don't double-install
if [[ "$PROMPT_COMMAND" != *"_capture_history"* ]]; then
    if [[ -n "$PROMPT_COMMAND" ]]; then
        _ORIGINAL_PROMPT_COMMAND="$PROMPT_COMMAND"
    fi
    PROMPT_COMMAND="_capture_history"
fi

# Aliases
alias history-search='shell-history search'
alias history-stats='shell-history stats'
alias history-flush='shell-history flush'

if [[ $- == *i* ]]; then
    echo "Shell History integration enabled."
fi
