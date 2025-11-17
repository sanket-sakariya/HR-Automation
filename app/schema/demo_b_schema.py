from __future__ import annotations
from typing import Optional
from uuid import UUID
from enum import Enum
from datetime import datetime
from pydantic import Field

from app.schema.baseapp_schema import BaseAppSchema


class DemoBStatus(str, Enum):
    """Allowed demo B status values."""

    CREATED = "created"
    UPDATING = "updating"
    UPDATED = "updated"
    DELETING = "deleting"
    DELETED = "deleted"


class DemoBCreateSchema(BaseAppSchema):
    """Schema for creating a new demo B."""

    name: str = Field(..., min_length=1, max_length=200, example="Sample Demo B")
    description: Optional[str] = Field(
        default=None, max_length=500, example="This is a sample demo B description."
    )
    is_active: Optional[bool] = Field(default=True, example=True)
    status: DemoBStatus = Field(
        ..., description="Current status of the entity", example=DemoBStatus.CREATED
    )


class DemoBUpdateSchema(BaseAppSchema):
    """Schema for updating an existing demo B."""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=200, example="Updated Demo B Name"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, example="This is an updated description."
    )
    is_active: Optional[bool] = Field(default=None, example=False)
    status: Optional[DemoBStatus] = Field(
        default=None,
        description="Current status of the entity",
        example=DemoBStatus.UPDATING,
    )


class DemoBStatusUpdateSchema(BaseAppSchema):
    """Schema for updating demo B status and error messages."""

    status: DemoBStatus = Field(
        ..., description="Current status of the entity", example=DemoBStatus.CREATED
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Technical error message for debugging",
        example="An unexpected error occurred.",
    )
    error_user_message: Optional[str] = Field(
        default=None,
        description="User-friendly error message for display",
        example="Something went wrong. Please try again.",
    )


class DemoBIsActiveUpdateSchema(BaseAppSchema):
    """Schema for updating demo B is_active status."""

    is_active: bool = Field(
        default=True, description="Whether the demo B is active", example=False
    )


class DemoBReadSchema(BaseAppSchema):
    """Schema for reading demo B details."""

    name: str = Field(..., min_length=1, max_length=200, example="Sample Demo B")
    description: Optional[str] = Field(
        default=None, max_length=500, example="This is a sample demo B description."
    )
    is_active: Optional[bool] = Field(default=True, example=True)
    status: DemoBStatus = Field(
        ..., description="Current status of the entity", example=DemoBStatus.CREATED
    )
    demo_b_id: UUID = Field(
        ..., description="Demo B ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d"
    )
    created_at: Optional[datetime] = Field(
        default=None, description="Created at", example="2023-01-01T12:00:00Z"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Updated at", example="2023-01-02T14:30:00Z"
    )
    deleted_at: Optional[datetime] = Field(
        default=None, description="Deleted at", example="2023-01-03T16:45:00Z"
    )
    deleted_by: Optional[UUID] = Field(
        default=None,
        description="Deleted by",
        example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d",
    )
