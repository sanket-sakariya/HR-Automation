from __future__ import annotations

from uuid import UUID
from typing import Optional, List, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

from app.schema.baseapp_schema import BaseAppSchema


class CandidateStatus(str, Enum):
    """Candidate status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class CandidateCreateSchema(BaseModel):
    """Schema for creating a new candidate."""

    job_requirement_id: UUID = Field(..., description="ID of the job requirement")
    first_name: str = Field(..., min_length=1, max_length=50, description="Candidate's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Candidate's last name")
    email: EmailStr = Field(..., description="Candidate's email address")
    phone: Optional[str] = Field(None, description="Candidate's phone number")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    portfolio_url: Optional[str] = Field(None, description="Portfolio website URL")
    current_location: Optional[str] = Field(None, description="Current location")
    willing_to_relocate: Optional[bool] = Field(False, description="Willing to relocate")
    skills: Optional[List[str]] = Field(None, description="List of skills")
    expected_salary: Optional[float] = Field(None, gt=0, description="Expected salary")
    notice_period: Optional[str] = Field(None, description="Notice period")


class CandidateReadSchema(BaseAppSchema):
    """Schema for reading candidate data."""

    candidate_id: UUID
    job_requirement_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    password: str  # Auto-generated 8-character password
    phone: Optional[str]
    linkedin_url: Optional[str]
    portfolio_url: Optional[str]
    current_location: Optional[str]
    willing_to_relocate: Optional[bool]
    skills: Optional[List[str]]
    expected_salary: Optional[float]
    notice_period: Optional[str]
    resume_url: Optional[str]
    candidate_resume_score: Optional[float]
    status: CandidateStatus
    
    # Test tracking fields
    aptitude_test: Optional[bool] = Field(None, description="Has taken aptitude test")
    technical_test: Optional[bool] = Field(None, description="Has taken technical test")
    hr_test: Optional[bool] = Field(None, description="Has taken HR test")
    
    # Test result fields - 'pass' or 'fail'
    aptitude_test_result: Optional[str] = Field(None, description="Aptitude test result: 'pass' or 'fail'")
    technical_test_result: Optional[str] = Field(None, description="Technical test result: 'pass' or 'fail'")
    hr_test_result: Optional[str] = Field(None, description="HR test result: 'pass' or 'fail'")

    # Numeric score fields (percentage 0-100) persisted on candidate row
    aptitude_test_score: Optional[float] = Field(None, description="Aptitude test score (0-100)")
    technical_test_score: Optional[float] = Field(None, description="Technical interview score (0-100)")
    hr_test_score: Optional[float] = Field(None, description="HR interview score (0-100)")

    # Resume selection field
    resume_selected: Optional[bool] = Field(None, description="Resume selected based on score")


class CandidateUpdateSchema(BaseModel):
    """Schema for updating candidate data."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None)
    linkedin_url: Optional[str] = Field(None)
    portfolio_url: Optional[str] = Field(None)
    current_location: Optional[str] = Field(None)
    willing_to_relocate: Optional[bool] = Field(None)
    skills: Optional[List[str]] = Field(None)
    expected_salary: Optional[float] = Field(None, gt=0)
    notice_period: Optional[str] = Field(None)
    resume_url: Optional[str] = Field(None, description="Path to resume file")
    candidate_resume_score: Optional[float] = Field(None, ge=0, le=100, description="AI-generated resume score")
    
    # Test tracking fields (optional updates)
    aptitude_test: Optional[bool] = Field(None, description="Has taken aptitude test")
    technical_test: Optional[bool] = Field(None, description="Has taken technical test")
    hr_test: Optional[bool] = Field(None, description="Has taken HR test")
    
    # Test result fields (optional updates) - 'pass' or 'fail'
    aptitude_test_result: Optional[str] = Field(None, description="Aptitude test result: 'pass' or 'fail'")
    technical_test_result: Optional[str] = Field(None, description="Technical test result: 'pass' or 'fail'")
    hr_test_result: Optional[str] = Field(None, description="HR test result: 'pass' or 'fail'")
    
    # Resume selection field
    resume_selected: Optional[bool] = Field(None, description="Resume selected based on score")


class CandidateListParamsSchema(BaseModel):
    """Schema for candidate list parameters."""

    page: int = Field(1, gt=0, description="Page number")
    limit: int = Field(20, gt=0, le=100, description="Items per page")
    search: Optional[str] = Field(None, description="Search term")
    status: Optional[CandidateStatus] = Field(None, description="Filter by status")
    job_requirement_id: Optional[UUID] = Field(None, description="Filter by job requirement")


class JobApplicationFormSchema(BaseModel):
    """Schema for job application form generation."""

    job_requirement_id: UUID = Field(..., description="ID of the job requirement to apply for")
