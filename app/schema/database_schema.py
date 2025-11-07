from __future__ import annotations
from typing import Optional
from enum import Enum
from pydantic import Field

from app.schema.baseapp_schema import BaseAppSchema


class DatabaseOperation(str, Enum):
    """Database operation types."""
    INITIALIZE = "initialize"
    UPGRADE = "upgrade"
    REVISION = "revision"


class DatabaseOperationRequestSchema(BaseAppSchema):
    """Schema for database operation requests."""
    
    operation: DatabaseOperation = Field(..., description="Type of database operation to perform")
    message: Optional[str] = Field(
        default=None, 
        description="Migration message (required for revision operation)"
    )
    revision: Optional[str] = Field(
        default="head",
        description="Target revision for upgrade operation (default: 'head')"
    )


class DatabaseOperationResponseSchema(BaseAppSchema):
    """Schema for database operation responses."""
    
    operation: str = Field(..., description="Operation that was performed")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Result message")
    revision_id: Optional[str] = Field(default=None, description="Created revision ID (for revision operation)")
    current_revision: Optional[str] = Field(default=None, description="Current database revision after operation")

