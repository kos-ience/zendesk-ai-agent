# CLAUDE.md - Guidelines for Claude Code

## Project Overview
This is a Zendesk AI Agent - a Python application that processes Zendesk tickets using OpenAI.

## Tech Stack
- **Language:** Python 3.11+
- **Testing:** pytest
- **Dependencies:** See pyproject.toml

## Project Structure
```
zendesk_ai_agent/
├── src/
│   ├── config.py          # Configuration management
│   ├── exceptions.py      # Custom exceptions
│   ├── logging_config.py  # Logging setup
│   ├── main.py            # Entry point
│   ├── models.py          # Data models
│   ├── openai_client.py   # OpenAI integration
│   ├── processor.py       # Ticket processing logic
│   └── zendesk_client.py  # Zendesk API client
├── tests/
│   └── test_*.py          # Unit tests
├── pyproject.toml         # Project configuration
└── CLAUDE.md              # This file
```

## Coding Standards

### DO:
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write descriptive docstrings for classes and functions
- Keep functions small and focused (single responsibility)
- Use meaningful variable names
- Handle exceptions appropriately with custom exception classes
- Write unit tests for new functionality

### DON'T:
- Don't use `print()` for logging - use the logging module
- Don't hardcode credentials or API keys
- Don't ignore exceptions silently
- Don't write overly complex one-liners
- Don't remove or skip tests to fix build failures
- Don't downgrade dependency versions

## Testing

Run tests with:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ -v --cov=src --cov-report=html
```

## When Fixing Build Failures

1. **Analyze the error** - Read the full stack trace
2. **Understand the root cause** - Don't just suppress the error
3. **Fix the actual bug** - Not the symptom
4. **Verify the fix** - Run the specific failing test
5. **Run all tests** - Ensure no regressions
6. **Commit with clear message** - Prefix with "Claude fix:"

## Environment Variables
- `ZENDESK_SUBDOMAIN` - Zendesk subdomain
- `ZENDESK_EMAIL` - Zendesk user email
- `ZENDESK_API_TOKEN` - Zendesk API token
- `OPENAI_API_KEY` - OpenAI API key

