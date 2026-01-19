"""Main entry point for the Zendesk AI Agent application."""

import argparse
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

from .config import get_settings, Settings
from .exceptions import ConfigurationError, ZendeskAIAgentError
from .logging_config import get_logger, setup_logging
from .openai_client import OpenAIClient
from .processor import TicketProcessor, TicketProcessorService
from .zendesk_client import ZendeskClient

logger = get_logger(__name__)

# Global service reference for signal handling
_service: Optional[TicketProcessorService] = None


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal", signal=signum)
    if _service:
        _service.stop()


def create_clients(settings: Settings) -> tuple[ZendeskClient, OpenAIClient]:
    """Create and configure API clients.

    Args:
        settings: Application settings.

    Returns:
        Tuple of (ZendeskClient, OpenAIClient).

    Raises:
        ConfigurationError: If client creation fails.
    """
    try:
        zendesk_client = ZendeskClient(settings.zendesk)
        openai_client = OpenAIClient(
            settings.openai,
            system_prompt=settings.app.system_prompt,
            langfuse_settings=settings.langfuse,
        )
        return zendesk_client, openai_client
    except Exception as e:
        raise ConfigurationError(f"Failed to create API clients: {e}") from e


def verify_connections(
    zendesk_client: ZendeskClient,
    openai_client: OpenAIClient,
) -> None:
    """Verify connections to both APIs.

    Args:
        zendesk_client: Zendesk API client.
        openai_client: OpenAI API client.

    Raises:
        ConfigurationError: If connection verification fails.
    """
    logger.info("Verifying API connections")

    try:
        zendesk_client.verify_connection()
    except Exception as e:
        raise ConfigurationError(f"Zendesk connection failed: {e}") from e

    try:
        openai_client.verify_connection()
    except Exception as e:
        raise ConfigurationError(f"OpenAI connection failed: {e}") from e

    logger.info("All API connections verified successfully")


def run_single_ticket(
    ticket_id: int,
    zendesk_client: ZendeskClient,
    openai_client: OpenAIClient,
    settings: Settings,
) -> int:
    """Process a single ticket and exit.

    Args:
        ticket_id: The Zendesk ticket ID to process.
        zendesk_client: Zendesk API client.
        openai_client: OpenAI API client.
        settings: Application settings.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    processor = TicketProcessor(zendesk_client, openai_client, settings.app)
    result = processor.process_ticket(ticket_id)

    if result.success:
        logger.info(
            "Ticket processed successfully",
            ticket_id=ticket_id,
            response_preview=result.response.response_text[:200] if result.response else None,
        )
        return 0
    else:
        logger.error(
            "Ticket processing failed",
            ticket_id=ticket_id,
            error=result.error_message,
        )
        return 1


def run_continuous(
    zendesk_client: ZendeskClient,
    openai_client: OpenAIClient,
    settings: Settings,
) -> int:
    """Run the continuous processing service.

    Args:
        zendesk_client: Zendesk API client.
        openai_client: OpenAI API client.
        settings: Application settings.

    Returns:
        Exit code (0 for clean shutdown).
    """
    global _service

    processor = TicketProcessor(zendesk_client, openai_client, settings.app)
    _service = TicketProcessorService(
        processor,
        poll_interval=settings.app.poll_interval_seconds,
    )

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        _service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        _service.stop()

    return 0


def hello() -> str:
    """Return a hello greeting message.

    Returns:
        A greeting message string.
    """
    return "Hello from Zendesk AI Agent!"


def run_batch(
    zendesk_client: ZendeskClient,
    openai_client: OpenAIClient,
    settings: Settings,
) -> int:
    """Run a single batch of ticket processing.

    Args:
        zendesk_client: Zendesk API client.
        openai_client: OpenAI API client.
        settings: Application settings.

    Returns:
        Exit code (0 if any tickets processed, 1 if all failed).
    """
    processor = TicketProcessor(zendesk_client, openai_client, settings.app)
    result = processor.process_new_tickets()

    if result.total_tickets == 0:
        logger.info("No tickets to process")
        return 0

    if result.failed == result.total_tickets:
        logger.error("All tickets failed to process")
        return 1

    return 0


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Zendesk AI Agent - Automated ticket response system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --service                    Run as continuous service
  %(prog)s --batch                      Process current tickets once
  %(prog)s --ticket 12345               Process a specific ticket
  %(prog)s --dry-run --batch            Test without posting responses
  %(prog)s --verify                     Verify API connections only
  %(prog)s --hello                      Print hello message and exit
        """,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--service",
        action="store_true",
        help="Run as continuous service (polls for new tickets)",
    )
    mode_group.add_argument(
        "--batch",
        action="store_true",
        help="Process current tickets once and exit",
    )
    mode_group.add_argument(
        "--ticket",
        type=int,
        metavar="ID",
        help="Process a specific ticket by ID",
    )
    mode_group.add_argument(
        "--verify",
        action="store_true",
        help="Verify API connections and exit",
    )
    mode_group.add_argument(
        "--hello",
        action="store_true",
        help="Print a hello message and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate responses but don't post to Zendesk",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    args = parse_args()

    # Handle hello mode early (no configuration needed)
    if args.hello:
        print(hello())
        return 0

    # Load environment variables
    load_dotenv(args.env_file)

    # Initialize settings and logging
    try:
        settings = get_settings()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Override dry-run from command line
    if args.dry_run:
        settings.app.dry_run = True

    # Setup logging
    setup_logging(settings.app.log_level)

    logger.info(
        "Zendesk AI Agent starting",
        mode="service" if args.service else "batch" if args.batch else "single",
        dry_run=settings.app.dry_run,
    )

    # Create clients
    try:
        zendesk_client, openai_client = create_clients(settings)
    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        return 1

    # Verify connections
    try:
        verify_connections(zendesk_client, openai_client)
    except ConfigurationError as e:
        logger.error("Connection verification failed", error=str(e))
        return 1

    # Handle verify-only mode
    if args.verify:
        logger.info("Connection verification successful")
        return 0

    # Run appropriate mode
    try:
        if args.service:
            return run_continuous(zendesk_client, openai_client, settings)
        elif args.batch:
            return run_batch(zendesk_client, openai_client, settings)
        elif args.ticket:
            return run_single_ticket(args.ticket, zendesk_client, openai_client, settings)
    except ZendeskAIAgentError as e:
        logger.error("Application error", error=str(e), details=e.details)
        return 1
    except Exception:
        logger.exception("Unexpected error")
        return 1
    finally:
        zendesk_client.close()
        openai_client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
