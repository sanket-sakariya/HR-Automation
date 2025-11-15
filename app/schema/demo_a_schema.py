from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from enum import Enum
from datetime import datetime, date
from pydantic import Field, EmailStr, AnyHttpUrl, BaseModel

from app.schema.baseapp_schema import (
    BaseAppSchema
)

class DemoAStatus(str, Enum):
    """Allowed image tag status values."""
    CREATED = "created"
    UPDATING = "updating" 
    UPDATED = "updated"
    DELETING = "deleting"
    DELETED = "deleted"

class SocialAccountSchema(BaseModel):
    """Schema for social account details."""
    platform: str = Field(..., min_length=1, max_length=50, example="twitter")
    username: str = Field(..., min_length=1, max_length=50, example="@sampleuser")
    url: AnyHttpUrl = Field(..., example="https://twitter.com/sampleuser")
    followers: int = Field(..., gt=0, example=1500)
    verified: bool = Field(..., example=True)

    class Config:
        """Pydantic configuration."""
        from_attributes = True

class PreferencesSchema(BaseModel):
    """Schema for user preferences."""
    newsletter: bool = Field(..., example=True)
    notifications_enabled: bool = Field(..., example=False)

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class DemoACreateSchema(BaseAppSchema):
    """Schema for creating a new demo."""

    name: str = Field(..., min_length=1, max_length=200, example="Sample Demo")
    description: Optional[str] = Field(default=None, max_length=500, example="This is a sample demo description.")
    website: Optional[AnyHttpUrl] = Field(default=None, example="https://example.com")
    email: Optional[EmailStr] = Field(default=None, example="user@example.com")
    age: Optional[int] = Field(default=None, gt=0, lt=150, example=30)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0, example=50.5)
    is_active: Optional[bool] = Field(default=True, example=True)
    status: DemoAStatus = Field(..., description="Current status of the entity", example=DemoAStatus.CREATED)
    start_date: Optional[date] = Field(default=None, example="2023-01-01")
    social_accounts: Optional[List[SocialAccountSchema]] = Field(default=None, example=[
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
    ])
    tags: Optional[List[str]] = Field(default=None, example=["postgres", "database", "example"])
    preferences: Optional[PreferencesSchema] = Field(default=None, example={
        "newsletter": True,
        "notifications_enabled": False
    })


class DemoAUpdateSchema(BaseAppSchema):
    """Schema for updating an existing demo."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200, example="Updated Demo Name")
    description: Optional[str] = Field(default=None, max_length=500, example="This is an updated description.")
    website: Optional[AnyHttpUrl] = Field(default=None, example="https://updated-example.com")
    email: Optional[EmailStr] = Field(default=None, example="updated-user@example.com")
    age: Optional[int] = Field(default=None, gt=0, lt=150, example=40)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0, example=75.5)
    is_active: Optional[bool] = Field(default=None, example=False)
    status: Optional[DemoStatus] = Field(default=None, description="Current status of the entity", example=DemoAStatus.UPDATING)
    start_date: Optional[date] = Field(default=None, example="2023-01-01")
    social_accounts: Optional[List[SocialAccountSchema]] = Field(default=None, example=[
        {
            "platform": "twitter",
            "username": "@updateduser",
            "url": "https://twitter.com/updateduser",
            "followers": 2000,
            "verified": True
        }
    ])
    tags: Optional[List[str]] = Field(default=None, example=["fastapi", "python"])
    preferences: Optional[PreferencesSchema] = Field(default=None, example={
        "newsletter": False,
        "notifications_enabled": True
    })

class DemoAStatusUpdateSchema(BaseAppSchema):
    """Schema for updating demo status and error messages."""

    status: DemoAStatus = Field(..., description="Current status of the entity", example=DemoAStatus.CREATED)
    error_message: Optional[str] = Field(default=None, description="Technical error message for debugging", example="An unexpected error occurred.")
    error_user_message: Optional[str] = Field(default=None, description="User-friendly error message for display", example="Something went wrong. Please try again.")


class DemoAIsActiveUpdateSchema(BaseAppSchema):
    """Schema for updating demo is_active status."""

    is_active: bool = Field(default=True, description="Whether the demo is active", example=False)


class DemoAListParamsSchema(BaseAppSchema):
    """Schema for demo list API parameters."""

    offset: int = Field(default=0, ge=0, description="Number of records to skip", example=0)
    limit: int = Field(default=100, ge=1, le=100, description="Number of items to return", example=10)
    order_by: str = Field(default="-created_at", description="Field to order by. Prefix with '-' for descending order", example="-name")
    search: Optional[str] = Field(default=None, description="Search query string to filter results", example="active")
    filters: Optional[List[str]] = Field(default=None, description="List of filter dicts as JSON strings", example=['{"field": "status", "operator": "eq", "value": "created"}'])


class DemoAReadSchema(BaseAppSchema):
    """Schema for reading demo details."""

    name: str = Field(..., min_length=1, max_length=200, example="Sample Demo")
    description: Optional[str] = Field(default=None, max_length=500, example="This is a sample demo description.")
    website: Optional[AnyHttpUrl] = Field(default=None, example="https://example.com")
    email: Optional[EmailStr] = Field(default=None, example="user@example.com")
    age: Optional[int] = Field(default=None, gt=0, lt=150, example=30)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0, example=50.5)
    is_active: Optional[bool] = Field(default=True, example=True)
    status: DemoAStatus = Field(..., description="Current status of the entity", example=DemoAStatus.CREATED)
    start_date: Optional[date] = Field(default=None, example="2023-01-01")
    social_accounts: Optional[List[SocialAccountSchema]] = Field(default=None, example=[
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
    ])
    tags: Optional[List[str]] = Field(default=None, example=["postgres", "database", "example"])
    preferences: Optional[PreferencesSchema] = Field(default=None, example={
        "newsletter": True,
        "notifications_enabled": False
    })
    demo_a_id: UUID = Field(..., description="Demo ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    created_at: Optional[datetime] = Field(default=None, description="Created at", example="2023-01-01T12:00:00Z")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at", example="2023-01-02T14:30:00Z")
    deleted_at: Optional[datetime] = Field(default=None, description="Deleted at", example="2023-01-03T16:45:00Z")
    deleted_by: Optional[UUID] = Field(default=None, description="Deleted by", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    status: Optional[DemoStatus]  = Field(..., description="Current status of the demo", example=DemoAStatus.CREATED)
    is_active: bool = Field(default=True, description="Whether the demo is active", example=True)
