from typing import Optional
from uuid import UUID

from fastapi import status

from app.exception.baseapp_exception import (
    BaseAppException,
    NotFoundException,
    AlreadyExistsException,
    InvalidDataException,
    PermissionDeniedException,
    ConflictException,
    InternalServerErrorException,
)


class DemoAException(BaseAppException):
    """Base exception for all DemoA related errors."""


class DemoANotFoundException(NotFoundException):
    """Exception for demo_a not found."""

    def __init__(self, demo_a_id: UUID):
        super().__init__("DemoA", resource_id=str(demo_a_id))


class DemoAAlreadyExistsException(AlreadyExistsException):
    """Exception for demo_a already exists."""

    def __init__(self, name: str):
        super().__init__("DemoA", field=f"name '{name}'")


class DemoACreationException(InternalServerErrorException):
    """Exception for demo_a creation failure."""

    def __init__(self, message: str = "Failed to create demo_a."):
        super().__init__(message=message)


class DemoAUpdateException(InternalServerErrorException):
    """Exception for demo_a update failure."""

    def __init__(self, demo_a_id: UUID, message: Optional[str] = None):
        message = f"Failed to update demo_a with ID {demo_a_id}."
        super().__init__(message=message)


class DemoADeletionException(InternalServerErrorException):
    """Exception for demo_a deletion failure."""

    def __init__(self, demo_a_id: UUID):
        super().__init__(f"Failed to delete demo_a with ID {demo_a_id}.")


class DemoAInvalidDataException(InvalidDataException):
    """Exception for invalid demo_a data."""

    def __init__(self, message: str = "Invalid demo_a data provided."):
        super().__init__(message=message)


class DemoAInactiveException(BaseAppException):
    """Exception for inactive demo_a."""

    def __init__(self, demo_a_id: UUID):
        super().__init__(
            f"DemoA with ID {demo_a_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoAPermissionDeniedException(PermissionDeniedException):
    """Exception for demo_a permission denied."""

    def __init__(
        self, message: str = "You do not have permission to access this demo_a."
    ):
        super().__init__(message=message)


class DemoAAccessForbiddenException(PermissionDeniedException):
    """Exception for demo_a access forbidden."""

    def __init__(self, message: str = "Access to this demo_a is forbidden."):
        super().__init__(message=message)


class DemoALimitExceededException(BaseAppException):
    """Exception for demo_a limit exceeded."""

    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            f"DemoA {limit_type} limit exceeded. Maximum allowed: {limit_value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoAAssignmentException(InternalServerErrorException):
    """Exception for demo_a assignment failure."""

    def __init__(self, message: str = "Failed to assign demo_a to user."):
        super().__init__(message=message)


class DemoADependencyException(ConflictException):
    """Exception for demo_a dependency."""

    def __init__(
        self, message: str = "Cannot delete demo_a because dependent resources exist."
    ):
        super().__init__(message=message)


class DemoAFileUploadException(BaseAppException):
    """Exception for demo_a file upload failure."""

    def __init__(self, message: str = "DemoA file upload failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAFileValidationException(BaseAppException):
    """Exception for demo_a file validation failure."""

    def __init__(self, message: str = "DemoA file validation failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAFileSizeExceededException(BaseAppException):
    """Exception for demo_a file size exceeded."""

    def __init__(self, max_size: int, actual_size: int):
        message = (
            f"File size {actual_size} bytes exceeds maximum allowed size of "
            f"{max_size} bytes for demo_a."
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAUnsupportedFileTypeException(BaseAppException):
    """Exception for demo_a unsupported file type."""

    def __init__(self, file_type: str, allowed_types: list):
        message = (
            f"File type '{file_type}' is not supported for demo_a. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAStorageException(BaseAppException):
    """Exception for demo_a storage operation failure."""

    def __init__(self, message: str = "DemoA storage operation failed."):
        super().__init__(
            message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DemoAFileNotFoundException(BaseAppException):
    """Exception for demo_a file not found."""

    def __init__(self, file_path: str):
        message = f"DemoA file not found: {file_path}"
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)
