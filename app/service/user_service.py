from __future__ import annotations

import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import log_user_activity

from app.schema.user_schema import (
    UserSignupSchema,
    UserLoginSchema,
    UserReadSchema,
    UserLoginResponseSchema,
    UserLogoutSchema,
)

from app.exception.user_exception import (
    UserNotFoundException,
    InvalidCredentialsException,
    UserInactiveException,
    UserNotLoggedInException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.user_repository import UserRepository


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, password_hash = stored_hash.split("$")
        expected_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash == expected_hash
    except ValueError:
        return False


def generate_access_token() -> str:
    """Generate a simple access token."""
    return secrets.token_urlsafe(32)


class UserService(BaseAppService):
    """User service for authentication operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.user_repo = UserRepository(db=db)

    # ==================== AUTHENTICATION OPERATIONS ====================

    async def signup(self, payload: UserSignupSchema) -> UserReadSchema:
        """Register a new user."""

        user_data = payload.model_dump()

        # Hash the password
        password = user_data.pop("password")
        user_data["password_hash"] = hash_password(password)

        # Generate workspace_id for the new user
        user_data["workspace_id"] = uuid.uuid4()

        user = await self.user_repo.insert(user_data=user_data)

        log_user_activity(
            f"User signed up: {user.username}",
            action_type="user_signup",
            level="info",
        )

        return UserReadSchema.model_validate(user)

    async def login(self, payload: UserLoginSchema) -> UserLoginResponseSchema:
        """Authenticate user and return tokens."""

        # Get user by email
        user = await self.user_repo.get_by_email(payload.email)
        if not user:
            raise InvalidCredentialsException()

        # Check if user is active
        if not user.is_active:
            raise UserInactiveException()

        # Verify password
        if not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsException()

        # Update login status
        user = await self.user_repo.update_login_status(
            user_id=user.user_id,
            is_logged_in=True,
            last_login_at=datetime.now(timezone.utc)
        )

        # Generate access token
        access_token = generate_access_token()

        log_user_activity(
            f"User logged in: {user.username}",
            action_type="user_login",
            level="info",
        )

        return UserLoginResponseSchema(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            workspace_id=user.workspace_id,
            access_token=access_token,
            token_type="bearer"
        )

    async def logout(self, user_id: UUID) -> UserLogoutSchema:
        """Logout user."""

        # Get user by ID
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=user_id)

        # Check if user is logged in
        if not user.is_logged_in:
            raise UserNotLoggedInException()

        # Update login status
        await self.user_repo.update_login_status(
            user_id=user_id,
            is_logged_in=False
        )

        log_user_activity(
            f"User logged out: {user.username}",
            action_type="user_logout",
            level="info",
        )

        return UserLogoutSchema(message="Successfully logged out")

    async def get_user(self, user_id: UUID) -> UserReadSchema:
        """Get user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id=user_id)
        return UserReadSchema.model_validate(user)
