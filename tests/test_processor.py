"""Tests for ticket processor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.config import AppSettings, ResponseStatus
from src.exceptions import OpenAIAPIError, ZendeskAPIError
from src.models import AIResponse, Ticket, TicketStatus
from src.processor import TicketProcessor


@pytest.fixture
def processor(
    mock_zendesk_client: MagicMock,
    mock_openai_client: MagicMock,
    app_settings: AppSettings,
) -> TicketProcessor:
    """Create a ticket processor with mock clients."""
    return TicketProcessor(mock_zendesk_client, mock_openai_client, app_settings)


class TestTicketProcessor:
    """Tests for TicketProcessor."""

    def test_process_ticket_success_dry_run(
        self,
        processor: TicketProcessor,
        mock_zendesk_client: MagicMock,
        mock_openai_client: MagicMock,
        sample_ticket: Ticket,
    ):
        """Test successful ticket processing in dry run mode."""
        mock_zendesk_client.get_ticket_with_comments.return_value = sample_ticket

        ai_response = AIResponse(
            ticket_id=sample_ticket.id,
            response_text="AI generated response",
            model_used="gpt-4-turbo-preview",
            tokens_used=100,
        )
        mock_openai_client.generate_response.return_value = ai_response

        result = processor.process_ticket(sample_ticket.id)

        assert result.success is True
        assert result.ticket_id == sample_ticket.id
        assert result.response == ai_response
        assert result.processing_time_ms > 0

        # Verify Zendesk was NOT called to add comment (dry run)
        mock_zendesk_client.add_comment.assert_not_called()

    def test_process_ticket_success_with_post(
        self,
        mock_zendesk_client: MagicMock,
        mock_openai_client: MagicMock,
        sample_ticket: Ticket,
    ):
        """Test successful ticket processing with actual post."""
        # Create settings with dry_run=False
        settings = AppSettings(
            dry_run=False,
            auto_publish_response=True,
            response_status=ResponseStatus.PENDING,
        )
        processor = TicketProcessor(mock_zendesk_client, mock_openai_client, settings)

        mock_zendesk_client.get_ticket_with_comments.return_value = sample_ticket

        ai_response = AIResponse(
            ticket_id=sample_ticket.id,
            response_text="AI generated response",
            model_used="gpt-4-turbo-preview",
            tokens_used=100,
        )
        mock_openai_client.generate_response.return_value = ai_response

        result = processor.process_ticket(sample_ticket.id)

        assert result.success is True

        # Verify Zendesk was called to add comment
        mock_zendesk_client.add_comment.assert_called_once_with(
            ticket_id=sample_ticket.id,
            body="AI generated response",
            public=True,
            status="pending",
            tags_to_add=["ai_processed", "ai_responded"],
        )

    def test_process_ticket_zendesk_error(
        self,
        processor: TicketProcessor,
        mock_zendesk_client: MagicMock,
    ):
        """Test handling of Zendesk API errors."""
        mock_zendesk_client.get_ticket_with_comments.side_effect = ZendeskAPIError(
            message="Ticket not found",
            status_code=404,
        )

        result = processor.process_ticket(99999)

        assert result.success is False
        assert "Zendesk error" in result.error_message
        assert result.ticket_id == 99999

    def test_process_ticket_openai_error(
        self,
        processor: TicketProcessor,
        mock_zendesk_client: MagicMock,
        mock_openai_client: MagicMock,
        sample_ticket: Ticket,
    ):
        """Test handling of OpenAI API errors."""
        mock_zendesk_client.get_ticket_with_comments.return_value = sample_ticket
        mock_openai_client.generate_response.side_effect = OpenAIAPIError(
            message="API error",
            error_type="internal_error",
        )

        result = processor.process_ticket(sample_ticket.id)

        assert result.success is False
        assert "OpenAI error" in result.error_message

    def test_process_new_tickets_success(
        self,
        processor: TicketProcessor,
        mock_zendesk_client: MagicMock,
        mock_openai_client: MagicMock,
    ):
        """Test batch processing of new tickets."""
        tickets = [
            Ticket(
                id=i,
                subject=f"Ticket {i}",
                description=f"Description {i}",
                status=TicketStatus.NEW,
                requester_id=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for i in range(1, 4)
        ]

        mock_zendesk_client.get_new_tickets.return_value = tickets
        mock_zendesk_client.get_ticket_with_comments.side_effect = tickets

        mock_openai_client.generate_response.return_value = AIResponse(
            ticket_id=0,
            response_text="Response",
            model_used="gpt-4",
            tokens_used=100,
        )

        result = processor.process_new_tickets()

        assert result.total_tickets == 3
        assert result.successful == 3
        assert result.failed == 0
        assert result.success_rate == 1.0

    def test_process_new_tickets_partial_failure(
        self,
        processor: TicketProcessor,
        mock_zendesk_client: MagicMock,
        mock_openai_client: MagicMock,
    ):
        """Test batch processing with some failures."""
        tickets = [
            Ticket(
                id=i,
                subject=f"Ticket {i}",
                description=f"Description {i}",
                status=TicketStatus.NEW,
                requester_id=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            for i in range(1, 4)
        ]

        mock_zendesk_client.get_new_tickets.return_value = tickets
        mock_zendesk_client.get_ticket_with_comments.side_effect = tickets

        # Fail on second ticket
        mock_openai_client.generate_response.side_effect = [
            AIResponse(
                ticket_id=1,
                response_text="Response 1",
                model_used="gpt-4",
                tokens_used=100,
            ),
            OpenAIAPIError(message="Error", error_type="internal"),
            AIResponse(
                ticket_id=3,
                response_text="Response 3",
                model_used="gpt-4",
                tokens_used=100,
            ),
        ]

        result = processor.process_new_tickets()

        assert result.total_tickets == 3
        assert result.successful == 2
        assert result.failed == 1

    def test_process_new_tickets_empty(
        self,
        processor: TicketProcessor,
        mock_zendesk_client: MagicMock,
    ):
        """Test batch processing with no tickets."""
        mock_zendesk_client.get_new_tickets.return_value = []

        result = processor.process_new_tickets()

        assert result.total_tickets == 0
        assert result.successful == 0
        assert result.failed == 0
