from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from pydantic import Field, ConfigDict, EmailStr, AnyHttpUrl, BaseModel

from app.schema.baseapp_schema import (
    BaseAppSchema
)


class SocialAccountSchema(BaseModel):
    platform: str
    username: str
    url: AnyHttpUrl
    followers: int
    verified: bool

class PreferencesSchema(BaseModel):
    newsletter: bool
    notifications_enabled: bool


class DemoCreateSchema(BaseAppSchema):
    """Schema for creating a new demo."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    website: Optional[AnyHttpUrl] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    age: Optional[int] = Field(default=None, gt=0, lt=150)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    is_active: Optional[bool] = Field(default=True)
    status: Optional[str] = Field(default="creating")
    start_date: Optional[date] = Field(default=None)
    social_accounts: Optional[List[SocialAccountSchema]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    preferences: Optional[PreferencesSchema] = Field(default=None)
    workspace_id: Optional[UUID] = Field(default=None)
    user_id: Optional[UUID] = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sample Demo",
                "description": "This is a sample demo description.",
                "website": "https://example.com",
                "email": "user@example.com",
                "age": 30,
                "progress": 50.5,
                "is_active": True,
                "status": "creating",
                "start_date": "2023-01-01",
                "social_accounts": [
                    {
                        "platform": "twitter",
                        "username": "@sampleuser",
                        "url": "https://twitter.com/sampleuser",
                        "followers": 1500,
                        "verified": True
                    }
                ],
                "tags": ["postgres", "database", "example"],
                "preferences": {
                    "newsletter": True,
                    "notifications_enabled": False
                },
                "workspace_id": "a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d",
                "user_id": "b3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4e"
            }
        }
    )


class DemoUpdateSchema(BaseAppSchema):
    """Schema for updating an existing demo."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    website: Optional[AnyHttpUrl] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    age: Optional[int] = Field(default=None, gt=0, lt=150)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    is_active: Optional[bool] = Field(default=None)
    status: Optional[str] = Field(default=None)
    start_date: Optional[date] = Field(default=None)
    social_accounts: Optional[List[SocialAccountSchema]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    preferences: Optional[PreferencesSchema] = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Demo Name",
                "description": "This is an updated description.",
                "tags": ["fastapi", "python"]
            }
        }
    )


class StatusSchema(BaseAppSchema):
    """Represents the current status of an entity."""

    status: str = Field(..., description="Current status of the entity")
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "created", "is_active": True}}
    )


class DemoStatusUpdateSchema(BaseAppSchema):
    """Schema for updating demo status and error messages."""

    status: str = Field(..., description="New status of the demo")
    error_message: Optional[str] = Field(default=None, description="Technical error message for debugging")
    error_user_message: Optional[str] = Field(default=None, description="User-friendly error message for display")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "updating",
                "error_message": "An unexpected error occurred.",
                "error_user_message": "Something went wrong. Please try again.",
            }
        }
    )


class DemoIsActiveUpdateSchema(BaseAppSchema):
    """Schema for updating demo is_active status."""

    is_active: bool = Field(default=True, description="Whether the demo is active")

    model_config = ConfigDict(
        json_schema_extra={"example": {"is_active": False}}
    )


class DemoListParamsSchema(BaseAppSchema):
    """Schema for demo list API parameters."""

    offset: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=100, description="Number of items to return")
    order_by: str = Field(default="-created_at", description="Field to order by. Prefix with '-' for descending order")
    search: Optional[str] = Field(default=None, description="Search query string to filter results")
    filters: Optional[List[str]] = Field(default=None, description="List of filter dicts as JSON strings")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "offset": 0,
                "limit": 10,
                "order_by": "-name",
                "search": "active",
                "filters": ['{"field": "status", "operator": "eq", "value": "created"}'],
            }
        }
    )


class DemoReadSchema(BaseAppSchema):
    """Schema for reading demo details."""

    demo_id: UUID = Field(..., description="Demo ID")
    name: str = Field(..., description="Demo name")
    description: Optional[str] = Field(default=None, description="Demo description")
    website: Optional[str] = Field(default=None, description="Demo website")
    email: Optional[EmailStr] = Field(default=None, description="Demo email")
    age: Optional[int] = Field(default=None, description="Demo age")
    progress: Optional[float] = Field(default=None, description="Demo progress")
    start_date: Optional[date] = Field(default=None, description="Demo start date")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at")
    deleted_by: Optional[UUID] = Field(default=None, description="Deleted by")
    status: str = Field(..., description="Current status of the demo")
    is_active: bool = Field(default=True, description="Whether the demo is active")
    social_accounts: Optional[List[SocialAccountSchema]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    preferences: Optional[PreferencesSchema] = Field(default=None)
    workspace_id: Optional[UUID] = Field(default=None)
    user_id: Optional[UUID] = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "demo_id": "a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d",
                "name": "Sample Demo",
                "description": "This is a sample demo description.",
                "website": "https://example.com",
                "email": "user@example.com",
                "age": 30,
                "progress": 50.5,
                "is_active": True,
                "status": "created",
                "start_date": "2023-01-01",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-02T14:30:00Z",
                "deleted_at": None,
                "deleted_by": None,
                "social_accounts": [
                    {
                        "platform": "twitter",
                        "username": "@sampleuser",
                        "url": "https://twitter.com/sampleuser",
                        "followers": 1500,
                        "verified": True
                    },
                    {
                        "platform": "github",
                        "username": "sampleuser",
                        "url": "https://github.com/sampleuser",
                        "followers": 250,
                        "verified": False
                    }
                ],
                "tags": ["postgres", "database", "example"],
                "preferences": {
                    "newsletter": True,
                    "notifications_enabled": False
                },
                "workspace_id": "a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d",
                "user_id": "b3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4e"
            }
        },
    )