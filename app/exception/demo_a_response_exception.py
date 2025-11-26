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


class DemoAResponseException(BaseAppException):
    """Base exception for all DemoAResponse related errors."""


class DemoAResponseNotFoundException(NotFoundException):
    """Exception for demo_a_response not found."""

    def __init__(self, demo_a_response_id: UUID):
        super().__init__("DemoAResponse", resource_id=str(demo_a_response_id))


class DemoAResponseAlreadyExistsException(AlreadyExistsException):
    """Exception for demo_a_response already exists."""

    def __init__(self, name: str):
        super().__init__("DemoAResponse", field=f"name '{name}'")


class DemoAResponseCreationException(InternalServerErrorException):
    """Exception for demo_a_response creation failure."""

    def __init__(self, message: str = "Failed to create demo_a_response."):
        super().__init__(message=message)


class DemoAResponseUpdateException(InternalServerErrorException):
    """Exception for demo_a_response update failure."""

    def __init__(self, demo_a_response_id: UUID, message: Optional[str] = None):
        message = f"Failed to update demo_a_response with ID {demo_a_response_id}."
        super().__init__(message=message)


class DemoAResponseDeletionException(InternalServerErrorException):
    """Exception for demo_a_response deletion failure."""

    def __init__(self, demo_a_response_id: UUID):
        super().__init__(
            f"Failed to delete demo_a_response with ID {demo_a_response_id}."
        )


class DemoAResponseInvalidDataException(InvalidDataException):
    """Exception for invalid demo_a_response data."""

    def __init__(self, message: str = "Invalid demo_a_response data provided."):
        super().__init__(message=message)


class DemoAResponseInactiveException(BaseAppException):
    """Exception for inactive demo_a_response."""

    def __init__(self, demo_a_response_id: UUID):
        super().__init__(
            f"DemoAResponse with ID {demo_a_response_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoAResponsePermissionDeniedException(PermissionDeniedException):
    """Exception for demo_a_response permission denied."""

    def __init__(
        self,
        message: str = "You do not have permission to access this demo_a_response.",
    ):
        super().__init__(message=message)


class DemoAResponseAccessForbiddenException(PermissionDeniedException):
    """Exception for demo_a_response access forbidden."""

    def __init__(self, message: str = "Access to this demo_a_response is forbidden."):
        super().__init__(message=message)


class DemoAResponseLimitExceededException(BaseAppException):
    """Exception for demo_a_response limit exceeded."""

    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            f"DemoAResponse {limit_type} limit exceeded. Maximum allowed: {limit_value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DemoAResponseAssignmentException(InternalServerErrorException):
    """Exception for demo_a_response assignment failure."""

    def __init__(self, message: str = "Failed to assign demo_a_response to user."):
        super().__init__(message=message)


class DemoAResponseDependencyException(ConflictException):
    """Exception for demo_a_response dependency."""

    def __init__(
        self,
        message: str = "Cannot delete demo_a_response because dependent resources exist.",
    ):
        super().__init__(message=message)


class DemoAResponseFileUploadException(BaseAppException):
    """Exception for demo_a_response file upload failure."""

    def __init__(self, message: str = "DemoAResponse file upload failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAResponseFileValidationException(BaseAppException):
    """Exception for demo_a_response file validation failure."""

    def __init__(self, message: str = "DemoAResponse file validation failed."):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAResponseFileSizeExceededException(BaseAppException):
    """Exception for demo_a_response file size exceeded."""

    def __init__(self, max_size: int, actual_size: int):
        message = (
            f"File size {actual_size} bytes exceeds maximum allowed size of "
            f"{max_size} bytes for demo_a_response."
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAResponseUnsupportedFileTypeException(BaseAppException):
    """Exception for demo_a_response unsupported file type."""

    def __init__(self, file_type: str, allowed_types: list):
        message = (
            f"File type '{file_type}' is not supported for demo_a_response. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class DemoAResponseStorageException(BaseAppException):
    """Exception for demo_a_response storage operation failure."""

    def __init__(self, message: str = "DemoAResponse storage operation failed."):
        super().__init__(
            message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DemoAResponseFileNotFoundException(BaseAppException):
    """Exception for demo_a_response file not found."""

    def __init__(self, file_path: str):
        message = f"DemoAResponse file not found: {file_path}"
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)
