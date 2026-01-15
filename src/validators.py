"""Custom validators for data models.

DEMO 2 SETUP:
=============
For Demo 2 with Dependabot:
1. Comment out the entire "PYDANTIC V2" section below (lines ~15-75)
2. Uncomment the entire "PYDANTIC V1" section at the bottom (lines ~80-140)
3. Also do the same in config.py
4. In pyproject.toml: swap pydantic to v1, comment out pydantic-settings
5. Push to main, then trigger Dependabot
"""


# =============================================================================
# PYDANTIC V2 (CURRENT - ACTIVE)
# =============================================================================
# For Demo 2: Comment out this entire section (lines 16-73)

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

# END OF PYDANTIC V2 SECTION
# =============================================================================


# =============================================================================
# PYDANTIC V1 (FOR DEMO 2 - UNCOMMENT THIS ENTIRE SECTION)
# =============================================================================
# For Demo 2: Uncomment this entire section (lines 84-138)

# from pydantic import BaseModel, validator


# class TicketInput(BaseModel):
#     """Validates ticket input data before processing."""
#     ticket_id: int
#     subject: str
#     priority: str

#     @validator('ticket_id')
#     def ticket_id_must_be_positive(cls, v):
#         """Ensure ticket ID is positive."""
#         if v <= 0:
#             raise ValueError('ticket_id must be positive')
#         return v

#     @validator('subject')
#     def subject_not_empty(cls, v):
#         """Ensure subject is not empty."""
#         if not v or not v.strip():
#             raise ValueError('subject cannot be empty')
#         return v.strip()

#     @validator('priority')
#     def priority_must_be_valid(cls, v):
#         """Ensure priority is valid."""
#         valid_priorities = ['low', 'normal', 'high', 'urgent']
#         if v.lower() not in valid_priorities:
#             raise ValueError(f'priority must be one of {valid_priorities}')
#         return v.lower()


# class ResponseConfig(BaseModel):
#     """Configuration for AI response generation."""
#     max_tokens: int
#     temperature: float

#     @validator('max_tokens')
#     def max_tokens_in_range(cls, v):
#         """Ensure max_tokens is within valid range."""
#         if v < 1 or v > 4096:
#             raise ValueError('max_tokens must be between 1 and 4096')
#         return v

#     @validator('temperature')
#     def temperature_in_range(cls, v):
#         """Ensure temperature is within valid range."""
#         if v < 0.0 or v > 2.0:
#             raise ValueError('temperature must be between 0.0 and 2.0')
#         return v

# END OF PYDANTIC V1 SECTION
# =============================================================================
