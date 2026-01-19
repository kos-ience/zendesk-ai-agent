"""Tests for main module."""

import pytest

from src.main import hello


class TestHello:
    """Tests for the hello function."""

    def test_hello_returns_greeting(self):
        """Test that hello returns the expected greeting message."""
        result = hello()
        assert result == "Hello from Zendesk AI Agent!"

    def test_hello_returns_string(self):
        """Test that hello returns a string type."""
        result = hello()
        assert isinstance(result, str)
