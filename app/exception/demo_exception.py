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

class DemoException(BaseAppException):
    """Base exception for all Demo related errors."""

class DemoNotFoundException(NotFoundException):
    """Exception for demo not found."""
    def __init__(self, demo_id: UUID):
        super().__init__("Demo", resource_id=str(demo_id))


class DemoAlreadyExistsException(AlreadyExistsException):
    """Exception for demo already exists."""
    def __init__(self, name: str):
        super().__init__("Demo", field=f"name '{name}'")


class DemoCreationException(InternalServerErrorException):
    """Exception for demo creation failure."""
    def __init__(self, message: str = "Failed to create demo."):
        super().__init__(message=message)


class DemoUpdateException(InternalServerErrorException):
    """Exception for demo update failure."""
    def __init__(self, demo_id: UUID, message: Optional[str] = None):
        message = f"Failed to update demo with ID {demo_id}."
        super().__init__(message=message)


class DemoDeletionException(InternalServerErrorException):
    """Exception for demo deletion failure."""
    def __init__(self, demo_id: UUID):
        super().__init__(f"Failed to delete demo with ID {demo_id}.")

class DemoInvalidDataException(InvalidDataException):
    """Exception for invalid demo data."""
    def __init__(self, message: str = "Invalid demo data provided."):
        super().__init__(message=message)


class DemoInactiveException(BaseAppException):
    """Exception for inactive demo."""
    def __init__(self, demo_id: UUID):
        super().__init__(f"Demo with ID {demo_id} is inactive.", status_code=status.HTTP_400_BAD_REQUEST)


class DemoPermissionDeniedException(PermissionDeniedException):
    """Exception for demo permission denied."""
    def __init__(self, message: str = "You do not have permission to access this demo."):
        super().__init__(message=message)


class DemoAccessForbiddenException(PermissionDeniedException):
    """Exception for demo access forbidden."""
    def __init__(self, message: str = "Access to this demo is forbidden."):
        super().__init__(message=message)

class DemoLimitExceededException(BaseAppException):
    """Exception for demo limit exceeded."""
    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            f"Demo {limit_type} limit exceeded. Maximum allowed: {limit_value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoAssignmentException(InternalServerErrorException):
    """Exception for demo assignment failure."""
    def __init__(self, message: str = "Failed to assign demo to user."):
        super().__init__(message=message)


class DemoDependencyException(ConflictException):
    """Exception for demo dependency."""
    def __init__(self, message: str = "Cannot delete demo because dependent resources exist."):
        super().__init__(message=message)



class DemoFileUploadException(BaseAppException):
    """Exception for demo file upload failure."""
    def __init__(self, message: str = "Demo file upload failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoFileValidationException(BaseAppException):
    """Exception for demo file validation failure."""
    def __init__(self, message: str = "Demo file validation failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoFileSizeExceededException(BaseAppException):
    """Exception for demo file size exceeded."""
    def __init__(self, max_size: int, actual_size: int):
        message = f"File size {actual_size} bytes exceeds maximum allowed size of {max_size} bytes for demo."
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoUnsupportedFileTypeException(BaseAppException):
    """Exception for demo unsupported file type."""
    def __init__(self, file_type: str, allowed_types: list):
        message = f"File type '{file_type}' is not supported for demo. Allowed types: {', '.join(allowed_types)}"
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoStorageException(BaseAppException):
    """Exception for demo storage operation failure."""
    def __init__(self, message: str = "Demo storage operation failed."):
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DemoFileNotFoundException(BaseAppException):
    """Exception for demo file not found."""
    def __init__(self, file_path: str):
        message = f"Demo file not found: {file_path}"
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)
