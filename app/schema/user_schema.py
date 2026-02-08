from __future__ import annotations
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import Field, EmailStr

from app.schema.baseapp_schema import BaseAppSchema


class UserSignupSchema(BaseAppSchema):
    """Schema for user signup."""

    username: str = Field(..., min_length=3, max_length=100, example="johndoe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    password: str = Field(..., min_length=8, example="SecurePass123!")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserLoginSchema(BaseAppSchema):
    """Schema for user login."""

    email: EmailStr = Field(..., example="john.doe@example.com")
    password: str = Field(..., min_length=8, example="SecurePass123!")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserReadSchema(BaseAppSchema):
    """Schema for reading user data."""

    user_id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    username: str = Field(..., example="johndoe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    workspace_id: Optional[UUID] = Field(default=None, example="123e4567-e89b-12d3-a456-426614174000")
    is_active: bool = Field(default=True, example=True)
    is_logged_in: bool = Field(default=False, example=False)
    last_login_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(...)
    updated_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserLoginResponseSchema(BaseAppSchema):
    """Schema for login response with user data and tokens."""

    user_id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    username: str = Field(..., example="johndoe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    workspace_id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserLogoutSchema(BaseAppSchema):
    """Schema for logout response."""

    message: str = Field(default="Successfully logged out", example="Successfully logged out")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
