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


class CompanyManagementException(BaseAppException):
    """Base exception for all Company Management related errors."""


class CompanyNotFoundException(NotFoundException):
    """Exception for company not found."""

    def __init__(self, company_id: UUID):
        super().__init__("Company", resource_id=str(company_id))


class CompanyAlreadyExistsException(AlreadyExistsException):
    """Exception for company already exists."""

    def __init__(self, email: str):
        super().__init__("Company", field=f"email '{email}'")


class CompanyCreationException(InternalServerErrorException):
    """Exception for company creation failure."""

    def __init__(self, message: str = "Failed to create company."):
        super().__init__(message=message)


class CompanyUpdateException(InternalServerErrorException):
    """Exception for company update failure."""

    def __init__(self, company_id: UUID, message: Optional[str] = None):
        message = message or f"Failed to update company with ID {company_id}."
        super().__init__(message=message)


class CompanyDeletionException(InternalServerErrorException):
    """Exception for company deletion failure."""

    def __init__(self, company_id: UUID):
        super().__init__(f"Failed to delete company with ID {company_id}.")


class CompanyInvalidDataException(InvalidDataException):
    """Exception for invalid company data."""

    def __init__(self, message: str = "Invalid company data provided."):
        super().__init__(message=message)


class CompanyInactiveException(BaseAppException):
    """Exception for inactive company."""

    def __init__(self, company_id: UUID):
        super().__init__(
            f"Company with ID {company_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


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


class CompanyPermissionDeniedException(PermissionDeniedException):
    """Exception for company permission denied."""

    def __init__(self, message: str = "You do not have permission to access this company."):
        super().__init__(message=message)


class JobRequirementPermissionDeniedException(PermissionDeniedException):
    """Exception for job requirement permission denied."""

    def __init__(self, message: str = "You do not have permission to access this job requirement."):
        super().__init__(message=message)
