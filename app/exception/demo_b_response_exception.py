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


class DemoBResponseException(BaseAppException):
    """Base exception for all DemoBResponse related errors."""


class DemoBResponseNotFoundException(NotFoundException):
    """Exception for demo_b_response not found."""

    def __init__(self, demo_b_response_id: UUID):
        super().__init__("DemoBResponse", resource_id=str(demo_b_response_id))


class DemoBResponseAlreadyExistsException(AlreadyExistsException):
    """Exception for demo_b_response already exists."""

    def __init__(self, name: str):
        super().__init__("DemoBResponse", field=f"name '{name}'")


class DemoBResponseCreationException(InternalServerErrorException):
    """Exception for demo_b_response creation failure."""

    def __init__(self, message: str = "Failed to create demo_b_response."):
        super().__init__(message=message)


class DemoBResponseUpdateException(InternalServerErrorException):
    """Exception for demo_b_response update failure."""

    def __init__(self, demo_b_response_id: UUID, message: Optional[str] = None):
        message = f"Failed to update demo_b_response with ID {demo_b_response_id}."
        super().__init__(message=message)


class DemoBResponseDeletionException(InternalServerErrorException):
    """Exception for demo_b_response deletion failure."""

    def __init__(self, demo_b_response_id: UUID):
        super().__init__(
            f"Failed to delete demo_b_response with ID {demo_b_response_id}."
        )


class DemoBResponseInvalidDataException(InvalidDataException):
    """Exception for invalid demo_b_response data."""

    def __init__(self, message: str = "Invalid demo_b_response data provided."):
        super().__init__(message=message)


class DemoBResponseInactiveException(BaseAppException):
    """Exception for inactive demo_b_response."""

    def __init__(self, demo_b_response_id: UUID):
        super().__init__(
            f"DemoBResponse with ID {demo_b_response_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoBResponsePermissionDeniedException(PermissionDeniedException):
    """Exception for demo_b_response permission denied."""

    def __init__(
        self,
        message: str = "You do not have permission to access this demo_b_response.",
    ):
        super().__init__(message=message)


class DemoBResponseAccessForbiddenException(PermissionDeniedException):
    """Exception for demo_b_response access forbidden."""

    def __init__(self, message: str = "Access to this demo_b_response is forbidden."):
        super().__init__(message=message)


class DemoBResponseLimitExceededException(BaseAppException):
    """Exception for demo_b_response limit exceeded."""

    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            f"DemoBResponse {limit_type} limit exceeded. Maximum allowed: {limit_value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoBResponseAssignmentException(InternalServerErrorException):
    """Exception for demo_b_response assignment failure."""

    def __init__(self, message: str = "Failed to assign demo_b_response to user."):
        super().__init__(message=message)


class DemoBResponseDependencyException(ConflictException):
    """Exception for demo_b_response dependency."""

    def __init__(
        self,
        message: str = "Cannot delete demo_b_response because dependent resources exist.",
    ):
        super().__init__(message=message)


class DemoBResponseFileUploadException(BaseAppException):
    """Exception for demo_b_response file upload failure."""

    def __init__(self, message: str = "DemoBResponse file upload failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBResponseFileValidationException(BaseAppException):
    """Exception for demo_b_response file validation failure."""

    def __init__(self, message: str = "DemoBResponse file validation failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBResponseFileSizeExceededException(BaseAppException):
    """Exception for demo_b_response file size exceeded."""

    def __init__(self, max_size: int, actual_size: int):
        message = (
            f"File size {actual_size} bytes exceeds maximum allowed size of "
            f"{max_size} bytes for demo_b_response."
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBResponseUnsupportedFileTypeException(BaseAppException):
    """Exception for demo_b_response unsupported file type."""

    def __init__(self, file_type: str, allowed_types: list):
        message = (
            f"File type '{file_type}' is not supported for demo_b_response. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoBResponseStorageException(BaseAppException):
    """Exception for demo_b_response storage operation failure."""

    def __init__(self, message: str = "DemoBResponse storage operation failed."):
        super().__init__(
            message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DemoBResponseFileNotFoundException(BaseAppException):
    """Exception for demo_b_response file not found."""

    def __init__(self, file_path: str):
        message = f"DemoBResponse file not found: {file_path}"
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)
