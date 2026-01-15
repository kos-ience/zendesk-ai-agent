"""Tests for custom validators."""

import pytest
from pydantic import ValidationError

from src.validators import TicketInput, ResponseConfig


class TestTicketInput:
    """Tests for TicketInput validator."""

    def test_valid_ticket_input(self):
        """Test valid ticket input passes validation."""
        ticket = TicketInput(
            ticket_id=123,
            subject="Help needed",
            priority="high"
        )
        assert ticket.ticket_id == 123
        assert ticket.subject == "Help needed"
        assert ticket.priority == "high"

    def test_invalid_ticket_id(self):
        """Test negative ticket ID fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TicketInput(ticket_id=-1, subject="Test", priority="normal")
        assert "ticket_id must be positive" in str(exc_info.value)

    def test_empty_subject(self):
        """Test empty subject fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TicketInput(ticket_id=1, subject="", priority="normal")
        assert "subject cannot be empty" in str(exc_info.value)

    def test_invalid_priority(self):
        """Test invalid priority fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TicketInput(ticket_id=1, subject="Test", priority="invalid")
        assert "priority must be one of" in str(exc_info.value)

    def test_priority_normalized_to_lowercase(self):
        """Test priority is normalized to lowercase."""
        ticket = TicketInput(ticket_id=1, subject="Test", priority="HIGH")
        assert ticket.priority == "high"


class TestResponseConfig:
    """Tests for ResponseConfig validator."""

    def test_valid_config(self):
        """Test valid config passes validation."""
        config = ResponseConfig(max_tokens=1000, temperature=0.7)
        assert config.max_tokens == 1000
        assert config.temperature == 0.7

    def test_max_tokens_too_low(self):
        """Test max_tokens below minimum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ResponseConfig(max_tokens=0, temperature=0.5)
        assert "max_tokens must be between" in str(exc_info.value)

    def test_max_tokens_too_high(self):
        """Test max_tokens above maximum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ResponseConfig(max_tokens=5000, temperature=0.5)
        assert "max_tokens must be between" in str(exc_info.value)

    def test_temperature_too_low(self):
        """Test temperature below minimum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ResponseConfig(max_tokens=100, temperature=-0.1)
        assert "temperature must be between" in str(exc_info.value)

    def test_temperature_too_high(self):
        """Test temperature above maximum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ResponseConfig(max_tokens=100, temperature=2.5)
        assert "temperature must be between" in str(exc_info.value)

