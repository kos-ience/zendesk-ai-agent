"""OpenAI API client with retry logic and error handling."""

from datetime import datetime, timezone
from typing import Optional

import langfuse
from openai import APIError, RateLimitError, APITimeoutError
from langfuse.openai import OpenAI  # Drop-in replacement with auto-tracing
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import OpenAISettings, LangfuseSettings
from .exceptions import (
    OpenAIAPIError,
    OpenAIContextLengthError,
    OpenAIRateLimitError,
)
from .logging_config import get_logger
from .models import AIResponse, Ticket

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a helpful and professional customer support agent. Your role is to:

1. Understand the customer's issue or question thoroughly
2. Provide clear, accurate, and helpful responses
3. Maintain a friendly and professional tone
4. Offer solutions or next steps when appropriate
5. Ask clarifying questions if the issue is unclear

Guidelines:
- Be concise but thorough
- Use simple, clear language
- Show empathy for the customer's situation
- If you don't know something, acknowledge it honestly
- Provide actionable steps when possible
- End with an offer to help further if needed

Format your response as a direct reply to the customer (don't include greetings like "Dear Customer" unless appropriate for the context)."""


class OpenAIClient:
    """Client for interacting with OpenAI API."""

    def __init__(
        self,
        settings: OpenAISettings,
        system_prompt: Optional[str] = None,
        langfuse_settings: Optional[LangfuseSettings] = None,
    ):
        """Initialize OpenAI client.

        Args:
            settings: OpenAI configuration settings.
            system_prompt: Custom system prompt (uses default if not provided).
            langfuse_settings: Optional Langfuse configuration for observability.
        """
        self.settings = settings
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._client: Optional[OpenAI] = None
        self._langfuse_settings = langfuse_settings
        self._langfuse_configured = False

    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client with Langfuse tracing."""
        if self._client is None:
            # Configure Langfuse once if settings provided
            if (
                not self._langfuse_configured
                and self._langfuse_settings
                and self._langfuse_settings.enabled
            ):
                langfuse.configure(
                    secret_key=self._langfuse_settings.secret_key.get_secret_value(),
                    public_key=self._langfuse_settings.public_key,
                    host=self._langfuse_settings.host,
                )
                self._langfuse_configured = True

            self._client = OpenAI(
                api_key=self.settings.api_key.get_secret_value(),
                timeout=float(self.settings.timeout),
            )
        return self._client

    def close(self) -> None:
        """Close the OpenAI client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "OpenAIClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @retry(
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def generate_response(self, ticket: Ticket) -> AIResponse:
        """Generate a response for a support ticket.

        Args:
            ticket: The ticket to generate a response for.

        Returns:
            AIResponse containing the generated text.

        Raises:
            OpenAIAPIError: If API request fails.
            OpenAIRateLimitError: If rate limit is exceeded.
            OpenAIContextLengthError: If input is too long.
        """
        logger.info(
            "Generating AI response",
            ticket_id=ticket.id,
            model=self.settings.model,
        )

        # Build the context from the ticket
        ticket_context = ticket.get_full_context()

        # Construct the user message
        user_message = f"""Please generate a helpful response to the following support ticket:

{ticket_context}

Generate a professional and helpful response that addresses the customer's needs."""

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.settings.max_tokens,
                temperature=self.settings.temperature,
            )

            # Extract response content
            response_text = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(
                "AI response generated",
                ticket_id=ticket.id,
                tokens_used=tokens_used,
                response_length=len(response_text),
            )

            return AIResponse(
                ticket_id=ticket.id,
                response_text=response_text,
                model_used=self.settings.model,
                tokens_used=tokens_used,
                generated_at=datetime.now(timezone.utc),
            )

        except RateLimitError as e:
            logger.warning("OpenAI rate limit exceeded", error=str(e))
            raise OpenAIRateLimitError() from e

        except APIError as e:
            error_message = str(e)

            # Check for context length error
            if "context_length" in error_message.lower() or "maximum context" in error_message.lower():
                logger.error(
                    "Context length exceeded",
                    ticket_id=ticket.id,
                    error=error_message,
                )
                raise OpenAIContextLengthError(error_message) from e

            logger.error(
                "OpenAI API error",
                ticket_id=ticket.id,
                error=error_message,
                status_code=getattr(e, "status_code", None),
            )
            raise OpenAIAPIError(
                message=error_message,
                error_type=type(e).__name__,
                status_code=getattr(e, "status_code", None),
            ) from e

    def generate_response_with_history(
        self,
        ticket: Ticket,
        conversation_history: list[dict],
    ) -> AIResponse:
        """Generate a response considering previous conversation history.

        Args:
            ticket: The ticket to generate a response for.
            conversation_history: List of previous messages in OpenAI format.

        Returns:
            AIResponse containing the generated text.

        Raises:
            OpenAIAPIError: If API request fails.
        """
        logger.info(
            "Generating AI response with history",
            ticket_id=ticket.id,
            history_length=len(conversation_history),
        )

        # Build messages list
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(conversation_history)

        # Add the current ticket context
        ticket_context = ticket.get_full_context()
        messages.append({
            "role": "user",
            "content": f"Latest ticket update:\n\n{ticket_context}\n\nPlease respond appropriately.",
        })

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=messages,
                max_tokens=self.settings.max_tokens,
                temperature=self.settings.temperature,
            )

            response_text = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            return AIResponse(
                ticket_id=ticket.id,
                response_text=response_text,
                model_used=self.settings.model,
                tokens_used=tokens_used,
                generated_at=datetime.now(timezone.utc),
            )

        except RateLimitError as e:
            raise OpenAIRateLimitError() from e
        except APIError as e:
            raise OpenAIAPIError(
                message=str(e),
                error_type=type(e).__name__,
                status_code=getattr(e, "status_code", None),
            ) from e

    def verify_connection(self) -> bool:
        """Verify connection to OpenAI API.

        Returns:
            True if connection is successful.

        Raises:
            OpenAIAPIError: If connection fails.
        """
        logger.info("Verifying OpenAI connection")

        try:
            # Make a simple API call to verify credentials
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )

            logger.info(
                "OpenAI connection verified",
                model=self.settings.model,
            )
            return True

        except APIError as e:
            logger.error("OpenAI connection failed", error=str(e))
            raise OpenAIAPIError(
                message=f"Failed to connect to OpenAI: {e}",
                error_type=type(e).__name__,
                status_code=getattr(e, "status_code", None),
            ) from e
