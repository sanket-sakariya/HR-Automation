from __future__ import annotations
from typing import Optional
from pydantic import Field

from app.schema.baseapp_schema import BaseAppSchema


class RevisionRequestSchema(BaseAppSchema):
    """Schema for revision creation requests."""
    message: str = Field(..., description="Migration message for the revision")


class MigrationResponseSchema(BaseAppSchema): 
    """Schema for migration responses."""
    operation: str = Field(..., description="Operation that was performed")
    success: bool = Field(default=False, description="Whether the operation was successful")
    message: str = Field(..., description="Result message")
    revision_id: Optional[str] = Field(default=None, description="Created revision ID (for revision operation)")
    current_revision: Optional[str] = Field(default=None, description="Current database revision after operation")
    file_count: Optional[int] = Field(default=None, description="Number of migration files processed")
    location: Optional[str] = Field(default=None, description="Location/path of the migration files")