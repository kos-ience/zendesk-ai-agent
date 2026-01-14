"""Tests for data models."""

from datetime import datetime, timezone

import pytest

from src.models import (
    AIResponse,
    BatchProcessingResult,
    ProcessingResult,
    Ticket,
    TicketComment,
    TicketPriority,
    TicketStatus,
)


class TestTicket:
    """Tests for Ticket model."""

    def test_ticket_creation(self, sample_ticket: Ticket):
        """Test basic ticket creation."""
        assert sample_ticket.id == 12345
        assert sample_ticket.subject == "Test Ticket Subject"
        assert sample_ticket.status == TicketStatus.NEW
        assert sample_ticket.priority == TicketPriority.NORMAL
        assert len(sample_ticket.comments) == 2

    def test_get_full_context(self, sample_ticket: Ticket):
        """Test full context generation."""
        context = sample_ticket.get_full_context()

        assert "Subject: Test Ticket Subject" in context
        assert "Priority: normal" in context
        assert "Status: new" in context
        assert "Initial Description:" in context
        assert "This is a test ticket description" in context
        assert "Conversation History:" in context
        assert "Initial message from customer" in context
        assert "Response from agent" in context

    def test_ticket_without_comments(self):
        """Test context generation without comments."""
        ticket = Ticket(
            id=1,
            subject="Simple ticket",
            description="Simple description",
            status=TicketStatus.OPEN,
            requester_id=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        context = ticket.get_full_context()
        assert "Simple ticket" in context
        assert "Conversation History:" not in context


class TestAIResponse:
    """Tests for AIResponse model."""

    def test_ai_response_creation(self):
        """Test AI response creation."""
        response = AIResponse(
            ticket_id=123,
            response_text="This is the AI response.",
            model_used="gpt-4-turbo-preview",
            tokens_used=150,
        )

        assert response.ticket_id == 123
        assert response.response_text == "This is the AI response."
        assert response.tokens_used == 150
        assert response.generated_at is not None


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_successful_result(self):
        """Test successful processing result."""
        ai_response = AIResponse(
            ticket_id=1,
            response_text="Response",
            model_used="gpt-4",
            tokens_used=100,
        )

        result = ProcessingResult(
            ticket_id=1,
            success=True,
            response=ai_response,
            processing_time_ms=500.5,
        )

        assert result.success is True
        assert result.error_message is None
        assert result.response is not None

    def test_failed_result(self):
        """Test failed processing result."""
        result = ProcessingResult(
            ticket_id=1,
            success=False,
            error_message="API error occurred",
            processing_time_ms=100.0,
        )

        assert result.success is False
        assert result.response is None
        assert result.error_message == "API error occurred"


class TestBatchProcessingResult:
    """Tests for BatchProcessingResult model."""

    def test_batch_result_success_rate(self):
        """Test success rate calculation."""
        results = [
            ProcessingResult(ticket_id=1, success=True, processing_time_ms=100),
            ProcessingResult(ticket_id=2, success=True, processing_time_ms=100),
            ProcessingResult(ticket_id=3, success=False, error_message="Error", processing_time_ms=100),
            ProcessingResult(ticket_id=4, success=True, processing_time_ms=100),
        ]

        batch = BatchProcessingResult(
            total_tickets=4,
            successful=3,
            failed=1,
            results=results,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

        assert batch.success_rate == 0.75

    def test_empty_batch_success_rate(self):
        """Test success rate with no tickets."""
        batch = BatchProcessingResult(
            total_tickets=0,
            successful=0,
            failed=0,
            results=[],
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

        assert batch.success_rate == 0.0
