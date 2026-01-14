"""Tests for Zendesk client."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.config import ZendeskSettings
from src.exceptions import (
    ZendeskAPIError,
    ZendeskAuthenticationError,
    ZendeskRateLimitError,
)
from src.zendesk_client import ZendeskClient


@pytest.fixture
def zendesk_client(zendesk_settings: ZendeskSettings) -> ZendeskClient:
    """Create Zendesk client for testing."""
    return ZendeskClient(zendesk_settings)


class TestZendeskClient:
    """Tests for ZendeskClient."""

    def test_base_url_construction(self, zendesk_client: ZendeskClient):
        """Test base URL is correctly constructed."""
        assert zendesk_client.base_url == "https://test-company.zendesk.com/api/v2"

    @patch("httpx.Client")
    def test_get_ticket_success(
        self,
        mock_client_class: MagicMock,
        zendesk_client: ZendeskClient,
    ):
        """Test successful ticket retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ticket": {
                "id": 123,
                "subject": "Test Subject",
                "description": "Test Description",
                "status": "new",
                "priority": "normal",
                "requester_id": 1,
                "assignee_id": 2,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T11:00:00Z",
                "tags": ["test"],
                "custom_fields": [],
            }
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        zendesk_client._client = mock_client

        ticket = zendesk_client.get_ticket(123)

        assert ticket.id == 123
        assert ticket.subject == "Test Subject"
        mock_client.get.assert_called_once_with("/tickets/123.json")

    @patch("httpx.Client")
    def test_get_ticket_auth_error(
        self,
        mock_client_class: MagicMock,
        zendesk_client: ZendeskClient,
    ):
        """Test authentication error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        zendesk_client._client = mock_client

        with pytest.raises(ZendeskAuthenticationError):
            zendesk_client.get_ticket(123)

    def test_handle_response_rate_limit(
        self,
        zendesk_client: ZendeskClient,
    ):
        """Test rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.text = "Rate limited"

        with pytest.raises(ZendeskRateLimitError) as exc_info:
            zendesk_client._handle_response_error(mock_response)

        assert exc_info.value.retry_after == 30

    @patch("httpx.Client")
    def test_add_comment_success(
        self,
        mock_client_class: MagicMock,
        zendesk_client: ZendeskClient,
    ):
        """Test successful comment addition."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.put.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        zendesk_client._client = mock_client

        zendesk_client.add_comment(
            ticket_id=123,
            body="Test comment",
            public=True,
            status="pending",
            tags_to_add=["ai_processed"],
        )

        mock_client.put.assert_called_once()
        call_args = mock_client.put.call_args
        assert call_args[0][0] == "/tickets/123.json"
        assert "comment" in call_args[1]["json"]["ticket"]
        assert call_args[1]["json"]["ticket"]["comment"]["body"] == "Test comment"

    @patch("httpx.Client")
    def test_get_new_tickets(
        self,
        mock_client_class: MagicMock,
        zendesk_client: ZendeskClient,
    ):
        """Test fetching new tickets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 1,
                    "subject": "Ticket 1",
                    "description": "Description 1",
                    "status": "new",
                    "requester_id": 1,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:00:00Z",
                },
                {
                    "id": 2,
                    "subject": "Ticket 2",
                    "description": "Description 2",
                    "status": "open",
                    "requester_id": 2,
                    "created_at": "2024-01-15T11:00:00Z",
                    "updated_at": "2024-01-15T11:00:00Z",
                },
            ]
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        zendesk_client._client = mock_client

        tickets = zendesk_client.get_new_tickets(limit=10)

        assert len(tickets) == 2
        assert tickets[0].id == 1
        assert tickets[1].id == 2

    def test_context_manager(self, zendesk_settings: ZendeskSettings):
        """Test client can be used as context manager."""
        with ZendeskClient(zendesk_settings) as client:
            assert client is not None
