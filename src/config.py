"""Configuration management using Pydantic Settings."""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ResponseStatus(str, Enum):
    """Zendesk ticket response status."""

    PENDING = "pending"
    OPEN = "open"
    SOLVED = "solved"
    HOLD = "hold"


class ZendeskSettings(BaseSettings):
    """Zendesk API configuration."""

    model_config = SettingsConfigDict(env_prefix="ZENDESK_")

    subdomain: str = Field(..., description="Zendesk subdomain")
    email: str = Field(..., description="Zendesk account email")
    api_token: SecretStr = Field(..., description="Zendesk API token")

    @field_validator("subdomain")
    @classmethod
    def validate_subdomain(cls, v: str) -> str:
        """Validate subdomain is not empty and has no special characters."""
        if not v or not v.strip():
            raise ValueError("Zendesk subdomain cannot be empty")
        if "." in v or "/" in v:
            raise ValueError("Subdomain should not contain dots or slashes")
        return v.strip().lower()


class OpenAISettings(BaseSettings):
    """OpenAI API configuration."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: SecretStr = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model to use")
    max_tokens: int = Field(default=1000, ge=1, le=4096, description="Max tokens in response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Model temperature")
    timeout: int = Field(default=60, ge=10, le=300, description="API timeout in seconds")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model name."""
        allowed_models = [
            "gpt-4-turbo-preview",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125",
        ]
        if v not in allowed_models:
            raise ValueError(f"Model must be one of: {', '.join(allowed_models)}")
        return v


class LangfuseSettings(BaseSettings):
    """Langfuse observability configuration."""

    model_config = SettingsConfigDict(env_prefix="LANGFUSE_")

    secret_key: SecretStr = Field(..., description="Langfuse secret key")
    public_key: str = Field(..., description="Langfuse public key")
    host: str = Field(
        default="http://localhost:3000",
        description="Langfuse server URL (self-hosted)"
    )
    enabled: bool = Field(default=True, description="Enable/disable Langfuse tracing")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is a valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Host must be a valid HTTP or HTTPS URL")
        return v.rstrip("/")


class AppSettings(BaseSettings):
    """Application-level configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    poll_interval_seconds: int = Field(
        default=60, ge=10, le=3600, description="Polling interval in seconds"
    )
    max_tickets_per_poll: int = Field(
        default=10, ge=1, le=100, description="Maximum tickets to process per poll"
    )
    dry_run: bool = Field(
        default=False, description="If true, don't actually post responses to Zendesk"
    )
    auto_publish_response: bool = Field(
        default=False, description="If true, publish response as public comment"
    )
    response_status: ResponseStatus = Field(
        default=ResponseStatus.PENDING, description="Status to set after responding"
    )
    system_prompt: Optional[str] = Field(
        default=None, description="Custom system prompt for OpenAI"
    )


class Settings(BaseSettings):
    """Combined application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    zendesk: ZendeskSettings = Field(default_factory=ZendeskSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    app: AppSettings = Field(default_factory=AppSettings)
    langfuse: Optional[LangfuseSettings] = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
