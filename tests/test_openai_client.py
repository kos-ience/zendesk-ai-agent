"""Tests for OpenAI client."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from src.config import OpenAISettings
from src.exceptions import OpenAIAPIError, OpenAIRateLimitError
from src.models import Ticket, TicketStatus
from src.openai_client import OpenAIClient


@pytest.fixture
def openai_client(openai_settings: OpenAISettings) -> OpenAIClient:
    """Create OpenAI client for testing."""
    return OpenAIClient(openai_settings)


class TestOpenAIClient:
    """Tests for OpenAIClient."""

    @patch("openai.OpenAI")
    def test_generate_response_success(
        self,
        mock_openai_class: MagicMock,
        openai_client: OpenAIClient,
        sample_ticket: Ticket,
    ):
        """Test successful response generation."""
        mock_choice = MagicMock()
        mock_choice.message.content = "This is the AI generated response."

        mock_usage = MagicMock()
        mock_usage.total_tokens = 250

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        openai_client._client = mock_client

        response = openai_client.generate_response(sample_ticket)

        assert response.ticket_id == sample_ticket.id
        assert response.response_text == "This is the AI generated response."
        assert response.tokens_used == 250
        assert response.model_used == "gpt-4-turbo-preview"

    @patch("openai.OpenAI")
    def test_generate_response_with_custom_prompt(
        self,
        mock_openai_class: MagicMock,
        openai_settings: OpenAISettings,
        sample_ticket: Ticket,
    ):
        """Test response generation with custom system prompt."""
        custom_prompt = "You are a specialized technical support agent."
        client = OpenAIClient(openai_settings, system_prompt=custom_prompt)

        mock_choice = MagicMock()
        mock_choice.message.content = "Technical response"

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = MagicMock(total_tokens=100)

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_openai_client

        client._client = mock_openai_client

        response = client.generate_response(sample_ticket)

        # Verify custom prompt was used
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert messages[0]["content"] == custom_prompt

    @patch("openai.OpenAI")
    def test_generate_response_rate_limit(
        self,
        mock_openai_class: MagicMock,
        openai_client: OpenAIClient,
        sample_ticket: Ticket,
    ):
        """Test rate limit error handling."""
        from openai import RateLimitError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
        mock_openai_class.return_value = mock_client

        openai_client._client = mock_client

        with pytest.raises(OpenAIRateLimitError):
            openai_client.generate_response(sample_ticket)

    @patch("openai.OpenAI")
    def test_generate_response_api_error(
        self,
        mock_openai_class: MagicMock,
        openai_client: OpenAIClient,
        sample_ticket: Ticket,
    ):
        """Test API error handling."""
        from openai import APIError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            message="API Error",
            request=MagicMock(),
            body=None,
        )
        mock_openai_class.return_value = mock_client

        openai_client._client = mock_client

        with pytest.raises(OpenAIAPIError):
            openai_client.generate_response(sample_ticket)

    @patch("openai.OpenAI")
    def test_verify_connection_success(
        self,
        mock_openai_class: MagicMock,
        openai_client: OpenAIClient,
    ):
        """Test successful connection verification."""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="Hi"))]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        openai_client._client = mock_client

        result = openai_client.verify_connection()

        assert result is True

    def test_context_manager(self, openai_settings: OpenAISettings):
        """Test client can be used as context manager."""
        with OpenAIClient(openai_settings) as client:
            assert client is not None
