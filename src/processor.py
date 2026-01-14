"""Ticket processor that orchestrates the Zendesk-OpenAI integration."""

import time
from datetime import datetime, timezone
from typing import Optional

from langfuse.decorators import observe, langfuse_context

from .config import AppSettings
from .exceptions import (
    OpenAIAPIError,
    TicketProcessingError,
    ZendeskAPIError,
)
from .logging_config import get_logger, log_context
from .models import (
    AIResponse,
    BatchProcessingResult,
    ProcessingResult,
    Ticket,
)
from .openai_client import OpenAIClient
from .zendesk_client import ZendeskClient

logger = get_logger(__name__)


class TicketProcessor:
    """Orchestrates ticket processing between Zendesk and OpenAI."""

    def __init__(
        self,
        zendesk_client: ZendeskClient,
        openai_client: OpenAIClient,
        settings: AppSettings,
    ):
        """Initialize the ticket processor.

        Args:
            zendesk_client: Configured Zendesk API client.
            openai_client: Configured OpenAI API client.
            settings: Application settings.
        """
        self.zendesk = zendesk_client
        self.openai = openai_client
        self.settings = settings

    @observe(name="process_ticket")
    def process_ticket(self, ticket_id: int) -> ProcessingResult:
        """Process a single ticket by ID.

        Args:
            ticket_id: The Zendesk ticket ID to process.

        Returns:
            ProcessingResult with success/failure status.
        """
        start_time = time.perf_counter()

        with log_context(ticket_id=ticket_id):
            logger.info("Processing ticket")

            try:
                # Fetch ticket with comments
                ticket = self.zendesk.get_ticket_with_comments(ticket_id)

                # Update Langfuse trace with ticket metadata (graceful if not configured)
                try:
                    langfuse_context.update_current_observation(
                        metadata={
                            "ticket_id": ticket.id,
                            "ticket_subject": ticket.subject,
                            "ticket_status": ticket.status.value if ticket.status else None,
                        }
                    )
                except Exception:
                    pass  # Langfuse not configured - continue without tracing metadata

                # Generate AI response
                ai_response = self.openai.generate_response(ticket)

                # Post response to Zendesk (unless dry run)
                if not self.settings.dry_run:
                    self._post_response(ticket, ai_response)
                else:
                    logger.info(
                        "Dry run - skipping Zendesk update",
                        response_preview=ai_response.response_text[:100],
                    )

                processing_time = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "Ticket processed successfully",
                    processing_time_ms=processing_time,
                )

                return ProcessingResult(
                    ticket_id=ticket_id,
                    success=True,
                    response=ai_response,
                    processing_time_ms=processing_time,
                )

            except ZendeskAPIError as e:
                logger.error("Zendesk API error", error=str(e))
                return self._create_failure_result(
                    ticket_id,
                    f"Zendesk error: {e.message}",
                    start_time,
                )

            except OpenAIAPIError as e:
                logger.error("OpenAI API error", error=str(e))
                return self._create_failure_result(
                    ticket_id,
                    f"OpenAI error: {e.message}",
                    start_time,
                )

            except Exception as e:
                logger.exception("Unexpected error processing ticket")
                return self._create_failure_result(
                    ticket_id,
                    f"Unexpected error: {str(e)}",
                    start_time,
                )

    @observe(name="batch_processing")
    def process_new_tickets(self) -> BatchProcessingResult:
        """Fetch and process all new tickets.

        Returns:
            BatchProcessingResult with all processing outcomes.
        """
        started_at = datetime.now(timezone.utc)
        logger.info(
            "Starting batch processing",
            max_tickets=self.settings.max_tickets_per_poll,
        )

        try:
            tickets = self.zendesk.get_new_tickets(self.settings.max_tickets_per_poll)
        except ZendeskAPIError as e:
            logger.error("Failed to fetch tickets", error=str(e))
            return BatchProcessingResult(
                total_tickets=0,
                successful=0,
                failed=0,
                results=[],
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        results = []
        for ticket in tickets:
            result = self.process_ticket(ticket.id)
            results.append(result)

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        batch_result = BatchProcessingResult(
            total_tickets=len(tickets),
            successful=successful,
            failed=failed,
            results=results,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Batch processing complete",
            total=batch_result.total_tickets,
            successful=batch_result.successful,
            failed=batch_result.failed,
            success_rate=f"{batch_result.success_rate:.1%}",
        )

        return batch_result

    @observe(name="post_zendesk_response")
    def _post_response(self, ticket: Ticket, response: AIResponse) -> None:
        """Post the AI response to Zendesk.

        Args:
            ticket: The original ticket.
            response: The AI-generated response.
        """
        # Determine new status
        new_status: Optional[str] = None
        if self.settings.response_status:
            new_status = self.settings.response_status.value

        # Add comment to ticket
        self.zendesk.add_comment(
            ticket_id=ticket.id,
            body=response.response_text,
            public=self.settings.auto_publish_response,
            status=new_status,
            tags_to_add=["ai_processed", "ai_responded"],
        )

        logger.info(
            "Response posted to Zendesk",
            ticket_id=ticket.id,
            public=self.settings.auto_publish_response,
            new_status=new_status,
        )

    def _create_failure_result(
        self,
        ticket_id: int,
        error_message: str,
        start_time: float,
    ) -> ProcessingResult:
        """Create a failure result.

        Args:
            ticket_id: The ticket ID.
            error_message: Description of the error.
            start_time: Processing start time for duration calculation.

        Returns:
            ProcessingResult indicating failure.
        """
        return ProcessingResult(
            ticket_id=ticket_id,
            success=False,
            error_message=error_message,
            processing_time_ms=(time.perf_counter() - start_time) * 1000,
        )


class TicketProcessorService:
    """Long-running service for continuous ticket processing."""

    def __init__(self, processor: TicketProcessor, poll_interval: int = 60):
        """Initialize the service.

        Args:
            processor: The ticket processor to use.
            poll_interval: Seconds between polling cycles.
        """
        self.processor = processor
        self.poll_interval = poll_interval
        self._running = False

    def start(self) -> None:
        """Start the continuous processing loop."""
        self._running = True
        logger.info(
            "Starting ticket processor service",
            poll_interval=self.poll_interval,
        )

        while self._running:
            try:
                self.processor.process_new_tickets()
            except Exception:
                logger.exception("Error in processing cycle")

            if self._running:
                logger.debug("Sleeping until next poll", seconds=self.poll_interval)
                time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the processing loop."""
        logger.info("Stopping ticket processor service")
        self._running = False
