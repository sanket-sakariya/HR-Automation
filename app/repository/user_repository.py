from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import DatabaseErrorMessages
from app.model.user_model import UserModel

from app.exception.user_exception import (
    UserNotFoundException,
    UserAlreadyExistsException,
    UserCreationException,
    UserUpdateException,
)
from app.exception.baseapp_exception import InternalServerErrorException


class UserRepository:
    """User repository for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert(self, user_data: Dict[str, Any]) -> UserModel:
        """Insert a new user (async)."""
        try:
            # Check if user with same email already exists
            existing_user = await self.get_by_email(user_data.get("email"))
            if existing_user:
                raise UserAlreadyExistsException(field=f"email '{user_data.get('email')}'")

            # Check if user with same username already exists
            existing_username = await self.get_by_username(user_data.get("username"))
            if existing_username:
                raise UserAlreadyExistsException(field=f"username '{user_data.get('username')}'")

            user = UserModel(**user_data)

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            return user
        except UserAlreadyExistsException:
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise UserCreationException(
                message=f"{DatabaseErrorMessages.USER_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(self, user_id: UUID) -> Optional[UserModel]:
        """Get a user by ID (async)."""
        try:
            query = select(UserModel).where(
                and_(
                    UserModel.user_id == user_id,
                    UserModel.is_active == True
                )
            ).limit(1)

            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            return user
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"Error retrieving user: {str(e)}"
            ) from e

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get a user by email (async)."""
        try:
            query = select(UserModel).where(
                UserModel.email == email
            ).limit(1)

            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            return user
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"Error retrieving user by email: {str(e)}"
            ) from e

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """Get a user by username (async)."""
        try:
            query = select(UserModel).where(
                UserModel.username == username
            ).limit(1)

            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            return user
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"Error retrieving user by username: {str(e)}"
            ) from e

    async def update_login_status(
        self,
        user_id: UUID,
        is_logged_in: bool,
        last_login_at: Optional[datetime] = None
    ) -> Optional[UserModel]:
        """Update user login status (async)."""
        try:
            update_data = {
                "is_logged_in": is_logged_in,
                "updated_at": datetime.now(timezone.utc)
            }
            if last_login_at:
                update_data["last_login_at"] = last_login_at

            stmt = (
                update(UserModel)
                .where(UserModel.user_id == user_id)
                .values(**update_data)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            return await self.get_by_id(user_id)
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise UserUpdateException(
                user_id=user_id,
                message=f"Failed to update login status: {str(e)}"
            ) from e

    async def update_workspace_id(
        self,
        user_id: UUID,
        workspace_id: UUID
    ) -> Optional[UserModel]:
        """Update user workspace ID (async)."""
        try:
            stmt = (
                update(UserModel)
                .where(UserModel.user_id == user_id)
                .values(
                    workspace_id=workspace_id,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()

            return await self.get_by_id(user_id)
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise UserUpdateException(
                user_id=user_id,
                message=f"Failed to update workspace ID: {str(e)}"
            ) from e
