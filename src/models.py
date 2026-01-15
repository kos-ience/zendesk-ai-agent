"""Data models for Zendesk tickets and responses."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketPriority(str, Enum):
    """Zendesk ticket priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, Enum):
    """Zendesk ticket status values."""

    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    HOLD = "hold"
    SOLVED = "solved"
    CLOSED = "closed"


class TicketComment(BaseModel):
    """Represents a comment on a Zendesk ticket."""

    id: int
    author_id: int
    body: str
    public: bool = True
    created_at: Optional[datetime] = None


class Ticket(BaseModel):
    """Represents a Zendesk ticket."""

    id: int
    subject: str
    description: str
    status: TicketStatus
    priority: Optional[TicketPriority] = None
    requester_id: int
    assignee_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    comments: list[TicketComment] = Field(default_factory=list)

    def get_full_context(self) -> str:
        """Get full ticket context including all comments."""
        context_parts = [
            f"Subject: {self.subject}",
            f"Priority: {self.priority.value if self.priority else 'normal'}",
            f"Status: {self.status.value}",
            f"Created: {self.created_at.isoformat()}",
            "",
            "Initial Description:",
            self.description,
        ]

        if self.comments:
            context_parts.append("")
            context_parts.append("Conversation History:")
            for comment in self.comments:
                timestamp = comment.created_at.isoformat() if comment.created_at else "Unknown"
                context_parts.append(f"\n[{timestamp}]")
                context_parts.append(comment.body)

        return "\n".join(context_parts)


class AIResponse(BaseModel):
    """Represents an AI-generated response."""

    ticket_id: int
    response_text: str
    model_used: str
    tokens_used: int
    confidence_score: Optional[float] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessingResult(BaseModel):
    """Result of processing a single ticket."""

    ticket_id: int
    success: bool
    response: Optional[AIResponse] = None
    error_message: Optional[str] = None
    processing_time_ms: float


class BatchProcessingResult(BaseModel):
    """Result of processing a batch of tickets."""

    total_tickets: int
    successful: int
    failed: int
    results: list[ProcessingResult]
    started_at: datetime
    completed_at: datetime

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tickets == 0:
            return 0.0
        return self.failed / self.total_tickets
