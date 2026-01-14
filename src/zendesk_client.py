"""Zendesk API client with retry logic and error handling."""

from datetime import datetime
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import ZendeskSettings
from .exceptions import (
    ZendeskAPIError,
    ZendeskAuthenticationError,
    ZendeskRateLimitError,
)
from .logging_config import get_logger
from .models import Ticket, TicketComment, TicketPriority, TicketStatus

logger = get_logger(__name__)


class ZendeskClient:
    """Client for interacting with Zendesk API."""

    def __init__(self, settings: ZendeskSettings):
        """Initialize Zendesk client.

        Args:
            settings: Zendesk configuration settings.
        """
        self.settings = settings
        self.base_url = f"https://{settings.subdomain}.zendesk.com/api/v2"
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                auth=(
                    f"{self.settings.email}/token",
                    self.settings.api_token.get_secret_value(),
                ),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self) -> "ZendeskClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Handle error responses from Zendesk API."""
        if response.status_code == 401:
            raise ZendeskAuthenticationError()
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise ZendeskRateLimitError(
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status_code >= 400:
            raise ZendeskAPIError(
                message=f"Zendesk API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

    @retry(
        retry=retry_if_exception_type(ZendeskRateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def get_ticket(self, ticket_id: int) -> Ticket:
        """Fetch a single ticket by ID.

        Args:
            ticket_id: The Zendesk ticket ID.

        Returns:
            Ticket object.

        Raises:
            ZendeskAPIError: If API request fails.
        """
        logger.info("Fetching ticket", ticket_id=ticket_id)

        response = self.client.get(f"/tickets/{ticket_id}.json")
        self._handle_response_error(response)

        data = response.json()["ticket"]
        return self._parse_ticket(data)

    @retry(
        retry=retry_if_exception_type(ZendeskRateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def get_new_tickets(self, limit: int = 10) -> list[Ticket]:
        """Fetch new/open tickets that need processing.

        Args:
            limit: Maximum number of tickets to fetch.

        Returns:
            List of Ticket objects.

        Raises:
            ZendeskAPIError: If API request fails.
        """
        logger.info("Fetching new tickets", limit=limit)

        # Search for new and open tickets, excluding those tagged as processed
        query = "type:ticket status<solved -tags:ai_processed"
        response = self.client.get(
            "/search.json",
            params={
                "query": query,
                "sort_by": "created_at",
                "sort_order": "asc",
                "per_page": limit,
            },
        )
        self._handle_response_error(response)

        data = response.json()
        tickets = [self._parse_ticket(t) for t in data.get("results", [])]

        logger.info("Fetched tickets", count=len(tickets))
        return tickets

    @retry(
        retry=retry_if_exception_type(ZendeskRateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def get_ticket_comments(self, ticket_id: int) -> list[TicketComment]:
        """Fetch all comments for a ticket.

        Args:
            ticket_id: The Zendesk ticket ID.

        Returns:
            List of TicketComment objects.

        Raises:
            ZendeskAPIError: If API request fails.
        """
        logger.debug("Fetching ticket comments", ticket_id=ticket_id)

        response = self.client.get(f"/tickets/{ticket_id}/comments.json")
        self._handle_response_error(response)

        data = response.json()
        comments = []
        for c in data.get("comments", []):
            comments.append(
                TicketComment(
                    id=c["id"],
                    author_id=c["author_id"],
                    body=c.get("body", ""),
                    public=c.get("public", True),
                    created_at=datetime.fromisoformat(
                        c["created_at"].replace("Z", "+00:00")
                    )
                    if c.get("created_at")
                    else None,
                )
            )

        return comments

    @retry(
        retry=retry_if_exception_type(ZendeskRateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    def add_comment(
        self,
        ticket_id: int,
        body: str,
        public: bool = False,
        status: Optional[str] = None,
        tags_to_add: Optional[list[str]] = None,
    ) -> None:
        """Add a comment to a ticket.

        Args:
            ticket_id: The Zendesk ticket ID.
            body: Comment body text.
            public: Whether the comment is public (visible to requester).
            status: Optional new status for the ticket.
            tags_to_add: Optional list of tags to add to the ticket.

        Raises:
            ZendeskAPIError: If API request fails.
        """
        logger.info(
            "Adding comment to ticket",
            ticket_id=ticket_id,
            public=public,
            status=status,
        )

        ticket_update: dict = {
            "comment": {
                "body": body,
                "public": public,
            }
        }

        if status:
            ticket_update["status"] = status

        if tags_to_add:
            ticket_update["additional_tags"] = tags_to_add

        response = self.client.put(
            f"/tickets/{ticket_id}.json",
            json={"ticket": ticket_update},
        )
        self._handle_response_error(response)

        logger.info("Comment added successfully", ticket_id=ticket_id)

    def get_ticket_with_comments(self, ticket_id: int) -> Ticket:
        """Fetch a ticket with all its comments.

        Args:
            ticket_id: The Zendesk ticket ID.

        Returns:
            Ticket object with comments populated.

        Raises:
            ZendeskAPIError: If API request fails.
        """
        ticket = self.get_ticket(ticket_id)
        ticket.comments = self.get_ticket_comments(ticket_id)
        return ticket

    def _parse_ticket(self, data: dict) -> Ticket:
        """Parse ticket data from API response.

        Args:
            data: Raw ticket data from API.

        Returns:
            Parsed Ticket object.
        """
        priority = None
        if data.get("priority"):
            try:
                priority = TicketPriority(data["priority"])
            except ValueError:
                pass

        return Ticket(
            id=data["id"],
            subject=data.get("subject", ""),
            description=data.get("description", ""),
            status=TicketStatus(data.get("status", "new")),
            priority=priority,
            requester_id=data["requester_id"],
            assignee_id=data.get("assignee_id"),
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ),
            tags=data.get("tags", []),
            custom_fields={
                cf["id"]: cf["value"] for cf in data.get("custom_fields", [])
            },
        )

    def verify_connection(self) -> bool:
        """Verify connection to Zendesk API.

        Returns:
            True if connection is successful.

        Raises:
            ZendeskAPIError: If connection fails.
        """
        logger.info("Verifying Zendesk connection")
        response = self.client.get("/users/me.json")
        self._handle_response_error(response)

        user_data = response.json().get("user", {})
        logger.info(
            "Zendesk connection verified",
            user_email=user_data.get("email"),
            user_name=user_data.get("name"),
        )
        return True
