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


class CandidateManagementException(BaseAppException):
    """Base exception for all Candidate Management related errors."""


class CandidateNotFoundException(NotFoundException):
    """Exception for candidate not found."""

    def __init__(self, candidate_id: UUID):
        super().__init__("Candidate", resource_id=str(candidate_id))


class CandidateAlreadyExistsException(AlreadyExistsException):
    """Exception for candidate already exists."""

    def __init__(self, email: str):
        super().__init__("Candidate", field=f"email '{email}'")


class CandidateCreationException(InternalServerErrorException):
    """Exception for candidate creation failure."""

    def __init__(self, message: str = "Failed to create candidate."):
        super().__init__(message=message)


class CandidateUpdateException(InternalServerErrorException):
    """Exception for candidate update failure."""

    def __init__(self, candidate_id: UUID, message: Optional[str] = None):
        message = message or f"Failed to update candidate with ID {candidate_id}."
        super().__init__(message=message)


class CandidateDeletionException(InternalServerErrorException):
    """Exception for candidate deletion failure."""

    def __init__(self, candidate_id: UUID):
        super().__init__(f"Failed to delete candidate with ID {candidate_id}.")


class CandidateInvalidDataException(InvalidDataException):
    """Exception for invalid candidate data."""

    def __init__(self, message: str = "Invalid candidate data provided."):
        super().__init__(message=message)


class CandidateInactiveException(BaseAppException):
    """Exception for inactive candidate."""

    def __init__(self, candidate_id: UUID):
        super().__init__(
            f"Candidate with ID {candidate_id} is inactive.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class CandidateProfileNotFoundException(NotFoundException):
    """Exception for candidate profile not found."""

    def __init__(self, candidate_profile_id: UUID):
        super().__init__("CandidateProfile", resource_id=str(candidate_profile_id))


class CandidateProfileCreationException(InternalServerErrorException):
    """Exception for candidate profile creation failure."""

    def __init__(self, message: str = "Failed to create candidate profile."):
        super().__init__(message=message)


class CandidateProfileUpdateException(InternalServerErrorException):
    """Exception for candidate profile update failure."""

    def __init__(self, candidate_profile_id: UUID, message: Optional[str] = None):
        message = message or f"Failed to update candidate profile with ID {candidate_profile_id}."
        super().__init__(message=message)


class CandidateProfileDeletionException(InternalServerErrorException):
    """Exception for candidate profile deletion failure."""

    def __init__(self, candidate_profile_id: UUID):
        super().__init__(f"Failed to delete candidate profile with ID {candidate_profile_id}.")


class CandidateProfileInvalidDataException(InvalidDataException):
    """Exception for invalid candidate profile data."""

    def __init__(self, message: str = "Invalid candidate profile data provided."):
        super().__init__(message=message)


class CandidatePermissionDeniedException(PermissionDeniedException):
    """Exception for candidate permission denied."""

    def __init__(self, message: str = "You do not have permission to access this candidate."):
        super().__init__(message=message)


class DuplicateApplicationException(ConflictException):
    """Exception for duplicate job application by same candidate."""

    def __init__(self, candidate_id: UUID, job_requirement_id: UUID):
        super().__init__(
            f"Candidate has already applied to this job.",
            status_code=409
        )


class CandidateProfilePermissionDeniedException(PermissionDeniedException):
    """Exception for candidate profile permission denied."""

    def __init__(self, message: str = "You do not have permission to access this candidate profile."):
        super().__init__(message=message)
