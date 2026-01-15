"""Custom validators for data models.

DEMO 2 SETUP (SIMPLIFIED):
==========================
Main branch: Pydantic v2 syntax (works with pydantic>=2.0.0)
For Demo 2: Just swap to v1 syntax below, create a PR, watch Claude fix it!

Note: pyproject.toml stays at pydantic>=2.0.0
      filterwarnings makes deprecation warnings fail tests
"""

# ===== PYDANTIC V2 (CURRENT - WORKING) =====
from pydantic import BaseModel, field_validator

# ===== PYDANTIC V1 (FOR DEMO 2 - SWAP THIS) =====
# from pydantic import BaseModel, validator


class TicketInput(BaseModel):
    """Validates ticket input data before processing."""
    
    ticket_id: int
    subject: str
    priority: str
    
    # ----- V2 SYNTAX (CURRENT) -----
    @field_validator('ticket_id')
    @classmethod
    def ticket_id_must_be_positive(cls, v):
        """Ensure ticket ID is positive."""
        if v <= 0:
            raise ValueError('ticket_id must be positive')
        return v
    
    # ----- V1 SYNTAX (FOR DEMO 2) -----
    # @validator('ticket_id')
    # def ticket_id_must_be_positive(cls, v):
    #     """Ensure ticket ID is positive."""
    #     if v <= 0:
    #         raise ValueError('ticket_id must be positive')
    #     return v
    
    # ----- V2 SYNTAX (CURRENT) -----
    @field_validator('subject')
    @classmethod
    def subject_not_empty(cls, v):
        """Ensure subject is not empty."""
        if not v or not v.strip():
            raise ValueError('subject cannot be empty')
        return v.strip()
    
    # ----- V1 SYNTAX (FOR DEMO 2) -----
    # @validator('subject')
    # def subject_not_empty(cls, v):
    #     """Ensure subject is not empty."""
    #     if not v or not v.strip():
    #         raise ValueError('subject cannot be empty')
    #     return v.strip()
    
    # ----- V2 SYNTAX (CURRENT) -----
    @field_validator('priority')
    @classmethod
    def priority_must_be_valid(cls, v):
        """Ensure priority is valid."""
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if v.lower() not in valid_priorities:
            raise ValueError(f'priority must be one of {valid_priorities}')
        return v.lower()
    
    # ----- V1 SYNTAX (FOR DEMO 2) -----
    # @validator('priority')
    # def priority_must_be_valid(cls, v):
    #     """Ensure priority is valid."""
    #     valid_priorities = ['low', 'normal', 'high', 'urgent']
    #     if v.lower() not in valid_priorities:
    #         raise ValueError(f'priority must be one of {valid_priorities}')
    #     return v.lower()


class ResponseConfig(BaseModel):
    """Configuration for AI response generation."""
    
    max_tokens: int
    temperature: float
    
    # ----- V2 SYNTAX (CURRENT) -----
    @field_validator('max_tokens')
    @classmethod
    def max_tokens_in_range(cls, v):
        """Ensure max_tokens is within valid range."""
        if v < 1 or v > 4096:
            raise ValueError('max_tokens must be between 1 and 4096')
        return v
    
    # ----- V1 SYNTAX (FOR DEMO 2) -----
    # @validator('max_tokens')
    # def max_tokens_in_range(cls, v):
    #     """Ensure max_tokens is within valid range."""
    #     if v < 1 or v > 4096:
    #         raise ValueError('max_tokens must be between 1 and 4096')
    #     return v
    
    # ----- V2 SYNTAX (CURRENT) -----
    @field_validator('temperature')
    @classmethod
    def temperature_in_range(cls, v):
        """Ensure temperature is within valid range."""
        if v < 0.0 or v > 2.0:
            raise ValueError('temperature must be between 0.0 and 2.0')
        return v
    
    # ----- V1 SYNTAX (FOR DEMO 2) -----
    # @validator('temperature')
    # def temperature_in_range(cls, v):
    #     """Ensure temperature is within valid range."""
    #     if v < 0.0 or v > 2.0:
    #         raise ValueError('temperature must be between 0.0 and 2.0')
    #     return v
