from __future__ import annotations
from typing import Optional
from uuid import UUID
from enum import Enum
from datetime import datetime
from pydantic import Field

from app.schema.baseapp_schema import BaseAppSchema


class MappingStatus(str, Enum):
    """Allowed mapping status values."""
    CREATED = "created"
    UPDATING = "updating"
    UPDATED = "updated"
    DELETING = "deleting"
    DELETED = "deleted"


class DemoAToDemoBMappingCreateSchema(BaseAppSchema):
    """Schema for creating a new mapping between DemoA and DemoB."""
    demo_a_id: UUID = Field(..., description="Demo A ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    demo_b_id: UUID = Field(..., description="Demo B ID", example="b4e9g7c1-4d2c-5f7g-9b3e-ad9f8g7b6c5e")
    is_active: Optional[bool] = Field(default=True, example=True)
    status: MappingStatus = Field(..., description="Current status of the mapping", example=MappingStatus.CREATED)


class DemoAToDemoBMappingUpdateSchema(BaseAppSchema):
    """Schema for updating an existing mapping."""
    demo_a_id: Optional[UUID] = Field(default=None, description="Demo A ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    demo_b_id: Optional[UUID] = Field(default=None, description="Demo B ID", example="b4e9g7c1-4d2c-5f7g-9b3e-ad9f8g7b6c5e")
    is_active: Optional[bool] = Field(default=None, example=False)
    status: Optional[MappingStatus] = Field(default=None, description="Current status of the mapping", example=MappingStatus.UPDATING)


class DemoAToDemoBMappingStatusUpdateSchema(BaseAppSchema):
    """Schema for updating mapping status and error messages."""
    status: MappingStatus = Field(..., description="Current status of the mapping", example=MappingStatus.CREATED)
    error_message: Optional[str] = Field(default=None, description="Technical error message for debugging", example="An unexpected error occurred.")
    error_user_message: Optional[str] = Field(default=None, description="User-friendly error message for display", example="Something went wrong. Please try again.")


class DemoAToDemoBMappingIsActiveUpdateSchema(BaseAppSchema):
    """Schema for updating mapping is_active status."""
    is_active: bool = Field(default=True, description="Whether the mapping is active", example=False)


class DemoAToDemoBMappingReadSchema(BaseAppSchema):
    """Schema for reading mapping details."""
    mapping_id: UUID = Field(..., description="Mapping ID", example="c5f0h8d2-5e3d-6g8h-0c4f-be0g9h8c7d6f")
    demo_a_id: UUID = Field(..., description="Demo A ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    demo_b_id: UUID = Field(..., description="Demo B ID", example="b4e9g7c1-4d2c-5f7g-9b3e-ad9f8g7b6c5e")
    is_active: bool = Field(default=True, description="Whether the mapping is active", example=True)
    status: MappingStatus = Field(..., description="Current status of the mapping", example=MappingStatus.CREATED)
    created_at: Optional[datetime] = Field(default=None, description="Created at", example="2023-01-01T12:00:00Z")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at", example="2023-01-02T14:30:00Z")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at", example="2023-01-03T16:45:00Z")
    deleted_by: Optional[UUID] = Field(default=None, description="Deleted by", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
