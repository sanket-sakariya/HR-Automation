from typing import Optional
from uuid import UUID

from fastapi import status

from app.exception.baseapp_exception import (
    BaseAppException,
    NotFoundException,
    AlreadyExistsException,
    InvalidDataException,
    UnauthorizedException,
    InternalServerErrorException,
)


class UserManagementException(BaseAppException):
    """Base exception for all User Management related errors."""


class UserNotFoundException(NotFoundException):
    """Exception for user not found."""

    def __init__(self, user_id: Optional[UUID] = None, email: Optional[str] = None):
        if user_id:
            super().__init__("User", resource_id=str(user_id))
        elif email:
            super().__init__("User", resource_id=f"email '{email}'")
        else:
            super().__init__("User")


class UserAlreadyExistsException(AlreadyExistsException):
    """Exception for user already exists."""

    def __init__(self, field: str = "email"):
        super().__init__("User", field=field)


class UserCreationException(InternalServerErrorException):
    """Exception for user creation failure."""

    def __init__(self, message: str = "Failed to create user."):
        super().__init__(message=message)


class UserUpdateException(InternalServerErrorException):
    """Exception for user update failure."""

    def __init__(self, user_id: UUID, message: Optional[str] = None):
        message = message or f"Failed to update user with ID {user_id}."
        super().__init__(message=message)


class InvalidCredentialsException(UnauthorizedException):
    """Exception for invalid login credentials."""

    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(message=message)


class UserInactiveException(BaseAppException):
    """Exception for inactive user account."""

    def __init__(self, message: str = "User account is inactive."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class InvalidPasswordException(InvalidDataException):
    """Exception for invalid password format."""

    def __init__(self, message: str = "Password does not meet requirements."):
        super().__init__(message=message)


class TokenExpiredException(UnauthorizedException):
    """Exception for expired authentication token."""

    def __init__(self, message: str = "Authentication token has expired."):
        super().__init__(message=message)


class InvalidTokenException(UnauthorizedException):
    """Exception for invalid authentication token."""

    def __init__(self, message: str = "Invalid authentication token."):
        super().__init__(message=message)


class UserNotLoggedInException(UnauthorizedException):
    """Exception when user is not logged in."""

    def __init__(self, message: str = "User is not logged in."):
        super().__init__(message=message)
