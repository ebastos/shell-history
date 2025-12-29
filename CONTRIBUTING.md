# Contributing to Shell History

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Getting Help](#getting-help)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:

- Be respectful and considerate
- Welcome newcomers and help them learn
- Focus on what's best for the community
- Accept constructive criticism gracefully

---

## How to Contribute

### 🐛 Reporting Bugs

Found a bug? Please [open an issue](https://github.com/your-username/shell-history/issues/new) with:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- Your environment (OS, shell, versions)
- Error messages or logs if available

### 💡 Suggesting Features

Have an idea? [Open a feature request](https://github.com/your-username/shell-history/issues/new) with:

- A clear description of the feature
- The problem it solves
- Example use cases
- Any implementation ideas (optional)

### 📖 Improving Documentation

Documentation improvements are always welcome! Feel free to:

- Fix typos or clarify wording
- Add examples
- Improve explanations
- Translate documentation

### 🔧 Submitting Code

Ready to contribute code? Here's the process:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes (following our [code style](#code-style))
4. Write or update tests
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. [Open a Pull Request](https://github.com/your-username/shell-history/compare)

---

## Development Setup

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete setup instructions.

**Quick start:**

```bash
# Clone and setup
git clone https://github.com/your-username/shell-history.git
cd shell-history

# Backend
cd backend && uv sync --extra dev && cd ..

# Client
cd client && go mod download && cd ..

# Start services
docker-compose up -d

# Run tests
cd backend && uv run pytest
```

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Code follows our style guidelines
- [ ] Documentation is updated (if needed)
- [ ] Commit messages are clear and descriptive

### PR Guidelines

1. **Title**: Clear, concise description (e.g., "Add search filter by date range")
2. **Description**: Explain what and why, not how
3. **Link issues**: Reference related issues with `Fixes #123` or `Relates to #456`
4. **Keep it focused**: One feature or fix per PR
5. **Be responsive**: Address review feedback promptly

### Review Process

1. A maintainer will review your PR
2. Feedback may be provided — this is collaborative, not adversarial
3. Once approved, your PR will be merged
4. Your contribution will be part of the next release 🎉

---

## Code Style

### Python

- **Type hints**: Required on all function signatures
- **Docstrings**: Google-style for public functions
- **Formatting**: Use `ruff format`
- **Linting**: Must pass `ruff check`
- **Imports**: Absolute imports, sorted by ruff

Example:

```python
def search_commands(
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> list[Command]:
    """Search commands by text query.

    Args:
        query: Search text
        limit: Maximum results to return
        offset: Number of results to skip

    Returns:
        List of matching commands
    """
    ...
```

### Go

- **Error handling**: Return errors, don't panic
- **Naming**: camelCase (unexported), PascalCase (exported)
- **Formatting**: Use `go fmt`
- **Documentation**: Comment exported functions

Example:

```go
// SearchCommands queries the API for matching commands.
func (c *Client) SearchCommands(query string, opts SearchOptions) ([]Command, error) {
    ...
}
```

### Commit Messages

Follow conventional commits:

```
feat: add search filter by hostname
fix: correct date parsing in stats endpoint
docs: update installation instructions
test: add tests for redaction service
refactor: extract command validation logic
```

---

## Getting Help

- 💬 [Open a discussion](https://github.com/your-username/shell-history/discussions) for questions
- 📖 Check [DEVELOPMENT.md](DEVELOPMENT.md) for technical details
- 🐛 [Open an issue](https://github.com/your-username/shell-history/issues) if you're stuck

---

**Thank you for contributing!** Every contribution, no matter how small, makes a difference. 🙏
