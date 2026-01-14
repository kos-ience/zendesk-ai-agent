"""Tests for configuration management."""

import pytest
from pydantic import SecretStr, ValidationError

from src.config import (
    AppSettings,
    LogLevel,
    OpenAISettings,
    ResponseStatus,
    ZendeskSettings,
)


class TestZendeskSettings:
    """Tests for ZendeskSettings."""

    def test_valid_settings(self):
        """Test valid Zendesk settings."""
        settings = ZendeskSettings(
            subdomain="test-company",
            email="test@example.com",
            api_token=SecretStr("secret-token"),
        )

        assert settings.subdomain == "test-company"
        assert settings.email == "test@example.com"
        assert settings.api_token.get_secret_value() == "secret-token"

    def test_subdomain_normalization(self):
        """Test subdomain is normalized."""
        settings = ZendeskSettings(
            subdomain="  Test-Company  ",
            email="test@example.com",
            api_token=SecretStr("token"),
        )

        assert settings.subdomain == "test-company"

    def test_invalid_subdomain_with_dot(self):
        """Test subdomain validation rejects dots."""
        with pytest.raises(ValidationError) as exc_info:
            ZendeskSettings(
                subdomain="test.company.zendesk.com",
                email="test@example.com",
                api_token=SecretStr("token"),
            )

        assert "should not contain dots" in str(exc_info.value)

    def test_empty_subdomain(self):
        """Test empty subdomain is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ZendeskSettings(
                subdomain="   ",
                email="test@example.com",
                api_token=SecretStr("token"),
            )

        assert "cannot be empty" in str(exc_info.value)


class TestOpenAISettings:
    """Tests for OpenAISettings."""

    def test_valid_settings(self):
        """Test valid OpenAI settings."""
        settings = OpenAISettings(
            api_key=SecretStr("sk-test-key"),
            model="gpt-4-turbo-preview",
            max_tokens=500,
            temperature=0.5,
        )

        assert settings.model == "gpt-4-turbo-preview"
        assert settings.max_tokens == 500
        assert settings.temperature == 0.5

    def test_default_values(self):
        """Test default values are applied."""
        settings = OpenAISettings(api_key=SecretStr("sk-test"))

        assert settings.model == "gpt-4-turbo-preview"
        assert settings.max_tokens == 1000
        assert settings.temperature == 0.7
        assert settings.timeout == 60

    def test_invalid_model(self):
        """Test invalid model is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAISettings(
                api_key=SecretStr("sk-test"),
                model="invalid-model",
            )

        assert "Model must be one of" in str(exc_info.value)

    def test_temperature_bounds(self):
        """Test temperature validation."""
        # Valid at boundaries
        settings_low = OpenAISettings(
            api_key=SecretStr("sk-test"),
            temperature=0.0,
        )
        assert settings_low.temperature == 0.0

        settings_high = OpenAISettings(
            api_key=SecretStr("sk-test"),
            temperature=2.0,
        )
        assert settings_high.temperature == 2.0

        # Invalid below
        with pytest.raises(ValidationError):
            OpenAISettings(
                api_key=SecretStr("sk-test"),
                temperature=-0.1,
            )

        # Invalid above
        with pytest.raises(ValidationError):
            OpenAISettings(
                api_key=SecretStr("sk-test"),
                temperature=2.1,
            )

    def test_max_tokens_bounds(self):
        """Test max tokens validation."""
        with pytest.raises(ValidationError):
            OpenAISettings(
                api_key=SecretStr("sk-test"),
                max_tokens=0,
            )

        with pytest.raises(ValidationError):
            OpenAISettings(
                api_key=SecretStr("sk-test"),
                max_tokens=5000,
            )


class TestAppSettings:
    """Tests for AppSettings."""

    def test_default_values(self):
        """Test default values."""
        settings = AppSettings()

        assert settings.log_level == LogLevel.INFO
        assert settings.poll_interval_seconds == 60
        assert settings.max_tickets_per_poll == 10
        assert settings.dry_run is False
        assert settings.auto_publish_response is False
        assert settings.response_status == ResponseStatus.PENDING

    def test_poll_interval_bounds(self):
        """Test poll interval validation."""
        # Valid
        settings = AppSettings(poll_interval_seconds=3600)
        assert settings.poll_interval_seconds == 3600

        # Too low
        with pytest.raises(ValidationError):
            AppSettings(poll_interval_seconds=5)

        # Too high
        with pytest.raises(ValidationError):
            AppSettings(poll_interval_seconds=7200)
