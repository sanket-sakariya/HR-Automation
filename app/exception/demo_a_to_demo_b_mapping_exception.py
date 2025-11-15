from typing import Optional
from uuid import UUID

from fastapi import status

from app.exception.baseapp_exception import (
    BaseAppException,
    AlreadyExistsException,
    InvalidDataException,
    PermissionDeniedException,
    ConflictException,
    InternalServerErrorException,
)

class DemoAToDemoBMappingException(BaseAppException):
    """Base exception for all Demo A to Demo B Mapping related errors."""

class DemoAToDemoBMappingNotFoundException(BaseAppException):
    """Exception for mapping not found."""
    def __init__(self, demo_a_to_demo_b_mapping_id: Optional[UUID] = None, message: Optional[str] = None):
        if message:
            # Custom message provided
            error_message = message
        elif demo_a_to_demo_b_mapping_id:
            # Standard ID-based message
            error_message = f"Mapping with ID {demo_a_to_demo_b_mapping_id} not found."
        else:
            # Default message
            error_message = "Mapping not found."
        super().__init__(message=error_message, status_code=status.HTTP_404_NOT_FOUND)


class DemoAToDemoBMappingAlreadyExistsException(AlreadyExistsException):
    """Exception for mapping already exists."""
    def __init__(self, demo_a_id: UUID, demo_b_id: UUID):
        super().__init__("Mapping", field=f"demo_a_id '{demo_a_id}' and demo_b_id '{demo_b_id}'")


class DemoAToDemoBMappingCreationException(InternalServerErrorException):
    """Exception for mapping creation failure."""
    def __init__(self, message: str = "Failed to create mapping."):
        super().__init__(message=message)


class DemoAToDemoBMappingUpdateException(InternalServerErrorException):
    """Exception for mapping update failure."""
    def __init__(self, demo_a_to_demo_b_mapping_id: UUID, message: Optional[str] = None):
        message = f"Failed to update mapping with ID {demo_a_to_demo_b_mapping_id}."
        super().__init__(message=message)


class DemoAToDemoBMappingDeletionException(InternalServerErrorException):
    """Exception for mapping deletion failure."""
    def __init__(self, demo_a_to_demo_b_mapping_id: UUID):
        super().__init__(f"Failed to delete mapping with ID {demo_a_to_demo_b_mapping_id}.")

class DemoAToDemoBMappingInvalidDataException(InvalidDataException):
    """Exception for invalid mapping data."""
    def __init__(self, message: str = "Invalid mapping data provided."):
        super().__init__(message=message)


class DemoAToDemoBMappingInactiveException(BaseAppException):
    """Exception for inactive mapping."""
    def __init__(self, demo_a_to_demo_b_mapping_id: UUID):
        super().__init__(f"Mapping with ID {demo_a_to_demo_b_mapping_id} is inactive.", status_code=status.HTTP_400_BAD_REQUEST)


class DemoAToDemoBMappingPermissionDeniedException(PermissionDeniedException):
    """Exception for mapping permission denied."""
    def __init__(self, message: str = "You do not have permission to access this mapping."):
        super().__init__(message=message)


class DemoAToDemoBMappingAccessForbiddenException(PermissionDeniedException):
    """Exception for mapping access forbidden."""
    def __init__(self, message: str = "Access to this mapping is forbidden."):
        super().__init__(message=message)

class DemoAToDemoBMappingDependencyException(ConflictException):
    """Exception for mapping dependency."""
    def __init__(self, message: str = "Cannot delete mapping because dependent resources exist."):
        super().__init__(message=message)