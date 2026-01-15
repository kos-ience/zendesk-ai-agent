"""Custom validators for data models - Uses Pydantic v2 syntax."""

from pydantic import BaseModel, field_validator


class TicketInput(BaseModel):
    """Validates ticket input data before processing."""
    
    ticket_id: int
    subject: str
    priority: str
    
    @field_validator('ticket_id')
    @classmethod
    def ticket_id_must_be_positive(cls, v):
        """Ensure ticket ID is positive."""
        if v <= 0:
            raise ValueError('ticket_id must be positive')
        return v
    
    @field_validator('subject')
    @classmethod
    def subject_not_empty(cls, v):
        """Ensure subject is not empty."""
        if not v or not v.strip():
            raise ValueError('subject cannot be empty')
        return v.strip()
    
    @field_validator('priority')
    @classmethod
    def priority_must_be_valid(cls, v):
        """Ensure priority is valid."""
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if v.lower() not in valid_priorities:
            raise ValueError(f'priority must be one of {valid_priorities}')
        return v.lower()


class ResponseConfig(BaseModel):
    """Configuration for AI response generation."""
    
    max_tokens: int
    temperature: float
    
    @field_validator('max_tokens')
    @classmethod
    def max_tokens_in_range(cls, v):
        """Ensure max_tokens is within valid range."""
        if v < 1 or v > 4096:
            raise ValueError('max_tokens must be between 1 and 4096')
        return v
    
    @field_validator('temperature')
    @classmethod
    def temperature_in_range(cls, v):
        """Ensure temperature is within valid range."""
        if v < 0.0 or v > 2.0:
            raise ValueError('temperature must be between 0.0 and 2.0')
        return v
