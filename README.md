# Zendesk AI Agent

A production-grade Python application that integrates Zendesk with OpenAI to automatically generate intelligent responses to support tickets.

## Features

- **Automated Ticket Processing**: Fetches new/open tickets from Zendesk and generates AI-powered responses
- **Flexible Operation Modes**: Run as a continuous service, batch processor, or single-ticket handler
- **Production Ready**: Includes comprehensive error handling, retry logic, structured logging, and configuration management
- **Dry Run Support**: Test responses without posting to Zendesk
- **Customizable**: Configure system prompts, response settings, and processing behavior

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Zendesk      │────▶│  Ticket         │────▶│    OpenAI       │
│    API          │     │  Processor      │     │    API          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │                       ▼                       │
        │              ┌─────────────────┐              │
        └──────────────│   Response      │◀─────────────┘
                       │   Posted        │
                       └─────────────────┘
```

## Installation

### Prerequisites

- Python 3.10 or higher
- Zendesk account with API access
- OpenAI API key

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd zendesk-ai-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

4. For development:
```bash
pip install -e ".[dev]"
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Required Configuration

| Variable | Description |
|----------|-------------|
| `ZENDESK_SUBDOMAIN` | Your Zendesk subdomain (e.g., `mycompany` for `mycompany.zendesk.com`) |
| `ZENDESK_EMAIL` | Email address for Zendesk authentication |
| `ZENDESK_API_TOKEN` | Zendesk API token |
| `OPENAI_API_KEY` | OpenAI API key |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | `gpt-4-turbo-preview` | OpenAI model to use |
| `OPENAI_MAX_TOKENS` | `1000` | Maximum tokens in response |
| `OPENAI_TEMPERATURE` | `0.7` | Model temperature (0.0-2.0) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `POLL_INTERVAL_SECONDS` | `60` | Seconds between polling cycles |
| `MAX_TICKETS_PER_POLL` | `10` | Maximum tickets per polling cycle |
| `DRY_RUN` | `false` | Generate responses without posting |
| `AUTO_PUBLISH_RESPONSE` | `false` | Post as public comment if true |
| `RESPONSE_STATUS` | `pending` | Ticket status after responding |

## Usage

### Verify Configuration

Test API connections without processing tickets:

```bash
zendesk-ai-agent --verify
```

### Process a Single Ticket

```bash
zendesk-ai-agent --ticket 12345
```

### Process Current Tickets (Batch Mode)

Process all new tickets once and exit:

```bash
zendesk-ai-agent --batch
```

### Run as Continuous Service

Poll for new tickets continuously:

```bash
zendesk-ai-agent --service
```

### Dry Run Mode

Generate responses without posting to Zendesk:

```bash
zendesk-ai-agent --dry-run --batch
```

### Custom Environment File

```bash
zendesk-ai-agent --env-file production.env --service
```

## Development

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=src --cov-report=html
```

### Code Quality

Format code:
```bash
black src tests
```

Lint code:
```bash
ruff check src tests
```

Type checking:
```bash
mypy src
```

## Project Structure

```
zendesk_ai_agent/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── exceptions.py       # Custom exceptions
│   ├── logging_config.py   # Structured logging setup
│   ├── main.py             # Entry point and CLI
│   ├── models.py           # Data models
│   ├── openai_client.py    # OpenAI API client
│   ├── processor.py        # Ticket processing logic
│   └── zendesk_client.py   # Zendesk API client
├── tests/
│   ├── conftest.py         # Test fixtures
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_openai_client.py
│   ├── test_processor.py
│   └── test_zendesk_client.py
├── .env.example
├── pyproject.toml
└── README.md
```

## Customization

### Custom System Prompt

Set a custom system prompt via environment variable:

```bash
export SYSTEM_PROMPT="You are a technical support specialist for a SaaS product..."
```

Or programmatically:

```python
from src.config import AppSettings
from src.openai_client import OpenAIClient

settings = OpenAISettings(api_key="...")
client = OpenAIClient(settings, system_prompt="Your custom prompt here")
```

### Ticket Filtering

By default, the agent processes tickets that:
- Have status `new` or `open`
- Are NOT tagged with `ai_processed`

Processed tickets are automatically tagged with:
- `ai_processed`
- `ai_responded`

## Error Handling

The application includes:

- **Automatic retries** for rate limits (Zendesk and OpenAI)
- **Exponential backoff** for transient failures
- **Graceful degradation** - failed tickets don't stop batch processing
- **Structured logging** for debugging and monitoring

## Security Considerations

- API tokens are stored as secrets and never logged
- Validate all configuration before use
- Use environment variables for sensitive data
- Consider using a secrets manager in production

## License

MIT License
