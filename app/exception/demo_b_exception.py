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


class DemoBException(BaseAppException):
    """Base exception for all DemoB related errors."""


class DemoBNotFoundException(NotFoundException):
    """Exception for demo_b not found."""

    def __init__(self, demo_b_id: UUID):
        super().__init__("DemoB", resource_id=str(demo_b_id))


class DemoBAlreadyExistsException(AlreadyExistsException):
    """Exception for demo_b already exists."""

    def __init__(self, name: str):
        super().__init__("DemoB", field=f"name '{name}'")


class DemoBCreationException(InternalServerErrorException):
    """Exception for demo_b creation failure."""

    def __init__(self, message: str = "Failed to create demo_b."):
        super().__init__(message=message)


class DemoBUpdateException(InternalServerErrorException):
    """Exception for demo_b update failure."""

    def __init__(self, demo_b_id: UUID, message: Optional[str] = None):
        message = f"Failed to update demo_b with ID {demo_b_id}."
        super().__init__(message=message)


class DemoBDeletionException(InternalServerErrorException):
    """Exception for demo_b deletion failure."""

    def __init__(self, demo_b_id: UUID):
        super().__init__(f"Failed to delete demo_b with ID {demo_b_id}.")


class DemoBInvalidDataException(InvalidDataException):
    """Exception for invalid demo_b data."""

    def __init__(self, message: str = "Invalid demo_b data provided."):
        super().__init__(message=message)


class DemoBInactiveException(BaseAppException):
    """Exception for inactive demo_b."""

    def __init__(self, demo_b_id: UUID):
        super().__init__(
            f"DemoB with ID {demo_b_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoBPermissionDeniedException(PermissionDeniedException):
    """Exception for demo_b permission denied."""

    def __init__(
        self, message: str = "You do not have permission to access this demo_b."
    ):
        super().__init__(message=message)


class DemoBAccessForbiddenException(PermissionDeniedException):
    """Exception for demo_b access forbidden."""

    def __init__(self, message: str = "Access to this demo_b is forbidden."):
        super().__init__(message=message)


class DemoBLimitExceededException(BaseAppException):
    """Exception for demo_b limit exceeded."""

    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            f"DemoB {limit_type} limit exceeded. Maximum allowed: {limit_value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoBAssignmentException(InternalServerErrorException):
    """Exception for demo_b assignment failure."""

    def __init__(self, message: str = "Failed to assign demo_b to user."):
        super().__init__(message=message)


class DemoBDependencyException(ConflictException):
    """Exception for demo_b dependency."""

    def __init__(
        self, message: str = "Cannot delete demo_b because dependent resources exist."
    ):
        super().__init__(message=message)


class DemoBFileUploadException(BaseAppException):
    """Exception for demo_b file upload failure."""

    def __init__(self, message: str = "DemoB file upload failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBFileValidationException(BaseAppException):
    """Exception for demo_b file validation failure."""

    def __init__(self, message: str = "DemoB file validation failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBFileSizeExceededException(BaseAppException):
    """Exception for demo_b file size exceeded."""

    def __init__(self, max_size: int, actual_size: int):
        message = (
            f"File size {actual_size} bytes exceeds maximum allowed size of "
            f"{max_size} bytes for demo_b."
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBUnsupportedFileTypeException(BaseAppException):
    """Exception for demo_b unsupported file type."""

    def __init__(self, file_type: str, allowed_types: list):
        message = (
            f"File type '{file_type}' is not supported for demo_b. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBStorageException(BaseAppException):
    """Exception for demo_b storage operation failure."""

    def __init__(self, message: str = "DemoB storage operation failed."):
        super().__init__(
            message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DemoBFileNotFoundException(BaseAppException):
    """Exception for demo_b file not found."""

    def __init__(self, file_path: str):
        message = f"DemoB file not found: {file_path}"
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)
