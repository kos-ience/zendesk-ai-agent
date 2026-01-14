"""Pytest fixtures and configuration."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from src.config import (
    AppSettings,
    LogLevel,
    OpenAISettings,
    ResponseStatus,
    Settings,
    ZendeskSettings,
)
from src.models import Ticket, TicketComment, TicketPriority, TicketStatus
from src.openai_client import OpenAIClient
from src.zendesk_client import ZendeskClient


@pytest.fixture
def zendesk_settings() -> ZendeskSettings:
    """Create test Zendesk settings."""
    return ZendeskSettings(
        subdomain="test-company",
        email="test@example.com",
        api_token=SecretStr("test-api-token"),
    )


@pytest.fixture
def openai_settings() -> OpenAISettings:
    """Create test OpenAI settings."""
    return OpenAISettings(
        api_key=SecretStr("test-openai-key"),
        model="gpt-4-turbo-preview",
        max_tokens=1000,
        temperature=0.7,
    )


@pytest.fixture
def app_settings() -> AppSettings:
    """Create test app settings."""
    return AppSettings(
        log_level=LogLevel.DEBUG,
        poll_interval_seconds=60,
        max_tickets_per_poll=10,
        dry_run=True,
        auto_publish_response=False,
        response_status=ResponseStatus.PENDING,
    )


@pytest.fixture
def settings(
    zendesk_settings: ZendeskSettings,
    openai_settings: OpenAISettings,
    app_settings: AppSettings,
) -> Settings:
    """Create complete test settings."""
    settings = MagicMock(spec=Settings)
    settings.zendesk = zendesk_settings
    settings.openai = openai_settings
    settings.app = app_settings
    return settings


@pytest.fixture
def sample_ticket() -> Ticket:
    """Create a sample ticket for testing."""
    return Ticket(
        id=12345,
        subject="Test Ticket Subject",
        description="This is a test ticket description with details about the issue.",
        status=TicketStatus.NEW,
        priority=TicketPriority.NORMAL,
        requester_id=100,
        assignee_id=200,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=datetime(2024, 1, 15, 12, 0, 0),
        tags=["test", "support"],
        custom_fields={},
        comments=[
            TicketComment(
                id=1,
                author_id=100,
                body="Initial message from customer",
                public=True,
                created_at=datetime(2024, 1, 15, 10, 30, 0),
            ),
            TicketComment(
                id=2,
                author_id=200,
                body="Response from agent",
                public=True,
                created_at=datetime(2024, 1, 15, 11, 0, 0),
            ),
        ],
    )


@pytest.fixture
def mock_zendesk_client(zendesk_settings: ZendeskSettings) -> MagicMock:
    """Create a mock Zendesk client."""
    client = MagicMock(spec=ZendeskClient)
    client.settings = zendesk_settings
    return client


@pytest.fixture
def mock_openai_client(openai_settings: OpenAISettings) -> MagicMock:
    """Create a mock OpenAI client."""
    client = MagicMock(spec=OpenAIClient)
    client.settings = openai_settings
    return client
