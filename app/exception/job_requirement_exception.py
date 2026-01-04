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


class JobRequirementException(BaseAppException):
    """Base exception for all Job Requirement related errors."""


class JobRequirementNotFoundException(NotFoundException):
    """Exception for job requirement not found."""

    def __init__(self, job_requirement_id: UUID):
        super().__init__("JobRequirement", resource_id=str(job_requirement_id))


class JobRequirementAlreadyExistsException(AlreadyExistsException):
    """Exception for job requirement already exists."""

    def __init__(self, title: str, company_id: UUID):
        super().__init__("JobRequirement", field=f"title '{title}' for company {company_id}")


class JobRequirementCreationException(InternalServerErrorException):
    """Exception for job requirement creation failure."""

    def __init__(self, message: str = "Failed to create job requirement."):
        super().__init__(message=message)


class JobRequirementUpdateException(InternalServerErrorException):
    """Exception for job requirement update failure."""

    def __init__(self, job_requirement_id: UUID, message: Optional[str] = None):
        message = message or f"Failed to update job requirement with ID {job_requirement_id}."
        super().__init__(message=message)


class JobRequirementDeletionException(InternalServerErrorException):
    """Exception for job requirement deletion failure."""

    def __init__(self, job_requirement_id: UUID):
        super().__init__(f"Failed to delete job requirement with ID {job_requirement_id}.")


class JobRequirementInvalidDataException(InvalidDataException):
    """Exception for invalid job requirement data."""

    def __init__(self, message: str = "Invalid job requirement data provided."):
        super().__init__(message=message)


class JobRequirementInactiveException(BaseAppException):
    """Exception for inactive job requirement."""

    def __init__(self, job_requirement_id: UUID):
        super().__init__(
            f"Job requirement with ID {job_requirement_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class JobRequirementPermissionDeniedException(PermissionDeniedException):
    """Exception for job requirement permission denied."""

    def __init__(self, message: str = "You do not have permission to access this job requirement."):
        super().__init__(message=message)


class JobRequirementAccessForbiddenException(PermissionDeniedException):
    """Exception for job requirement access forbidden."""

    def __init__(self, message: str = "Access to this job requirement is forbidden."):
        super().__init__(message=message)


class JobRequirementLimitExceededException(BaseAppException):
    """Exception for job requirement limit exceeded."""

    def __init__(self, limit_type: str, limit_value: int):
        super().__init__(
            f"Job requirement {limit_type} limit exceeded. Maximum allowed: {limit_value}.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class JobRequirementDependencyException(ConflictException):
    """Exception for job requirement dependency."""

    def __init__(
        self, message: str = "Cannot delete job requirement because dependent resources exist."
    ):
        super().__init__(message=message)
