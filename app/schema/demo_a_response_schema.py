from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from enum import Enum
from datetime import datetime
from pydantic import Field

from app.schema.baseapp_schema import BaseAppSchema


class DemoAResponseStatus(str, Enum):
    """Allowed demo A response status values."""

    CREATED = "created"
    UPDATING = "updating"
    UPDATED = "updated"
    DELETING = "deleting"
    DELETED = "deleted"


class DemoAResponseCreateSchema(BaseAppSchema):
    """Schema for creating a new demo A response."""

    demo_a_id: UUID = Field(..., description="Demo A ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    name: str = Field(..., min_length=1, max_length=200, example="Sample Demo A Response")
    description: Optional[str] = Field(
        default=None, max_length=500, example="This is a sample demo A response description."
    )
    is_active: Optional[bool] = Field(default=True, example=True)
    status: DemoAResponseStatus = Field(
        ..., description="Current status of the entity", example=DemoAResponseStatus.CREATED
    )


class DemoAResponseUpdateSchema(BaseAppSchema):
    """Schema for updating an existing demo A response."""

    demo_a_id: Optional[UUID] = Field(default=None, description="Demo A ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    name: Optional[str] = Field(
        default=None, min_length=1, max_length=200, example="Updated Demo A Response Name"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, example="This is an updated description."
    )
    is_active: Optional[bool] = Field(default=None, example=False)
    status: Optional[DemoAResponseStatus] = Field(
        default=None,
        description="Current status of the entity",
        example=DemoAResponseStatus.UPDATING,
    )


class DemoAResponseStatusUpdateSchema(BaseAppSchema):
    """Schema for updating demo A response status and error messages."""

    status: DemoAResponseStatus = Field(
        ..., description="Current status of the entity", example=DemoAResponseStatus.CREATED
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


class DemoAResponseIsActiveUpdateSchema(BaseAppSchema):
    """Schema for updating demo A response is_active status."""

    is_active: bool = Field(
        default=True, description="Whether the demo A response is active", example=False
    )


class DemoAResponseListParamsSchema(BaseAppSchema):
    """Schema for demo A response list API parameters."""

    offset: int = Field(
        default=0, ge=0, description="Number of records to skip", example=0
    )
    limit: int = Field(
        default=100, ge=1, le=100, description="Number of items to return", example=10
    )
    order_by: str = Field(
        default="-created_at",
        description="Field to order by. Prefix with '-' for descending order",
        example="-name",
    )
    search: Optional[str] = Field(
        default=None,
        description="Search query string to filter results",
        example="active",
    )
    filters: Optional[List[str]] = Field(
        default=None,
        description="List of filter dicts as JSON strings",
        example=['{"field": "status", "operator": "eq", "value": "created"}'],
    )


class DemoAResponseReadSchema(BaseAppSchema):
    """Schema for reading demo A response details."""

    demo_a_id: UUID = Field(..., description="Demo A ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    name: str = Field(..., min_length=1, max_length=200, example="Sample Demo A Response")
    description: Optional[str] = Field(
        default=None, max_length=500, example="This is a sample demo A response description."
    )
    is_active: Optional[bool] = Field(default=True, example=True)
    status: DemoAResponseStatus = Field(
        ..., description="Current status of the entity", example=DemoAResponseStatus.CREATED
    )
    demo_a_response_id: UUID = Field(
        ..., description="Demo A Response ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d"
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


DemoAResponseCreateSchema.model_rebuild()
DemoAResponseUpdateSchema.model_rebuild()
DemoAResponseReadSchema.model_rebuild()

