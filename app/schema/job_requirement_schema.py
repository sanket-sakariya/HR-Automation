from __future__ import annotations
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from datetime import datetime
from pydantic import Field, BaseModel

from app.schema.baseapp_schema import BaseAppSchema


class JobRequirementStatus(str, Enum):
    """Allowed job requirement status values."""
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class SkillRequirementSchema(BaseModel):
    """Schema for skill requirements."""

    skill: str = Field(..., min_length=1, max_length=100, example="Python")
    level: str = Field(
        ...,
        enum=["beginner", "intermediate", "advanced", "expert"],
        example="intermediate"
    )
    required: bool = Field(default=True, example=True)

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ExperienceSchema(BaseModel):
    """Schema for experience requirements."""

    min_years: Optional[int] = Field(default=None, ge=0, example=2)
    max_years: Optional[int] = Field(default=None, ge=0, example=5)
    preferred: Optional[int] = Field(default=None, ge=0, example=3)

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class SalaryRangeSchema(BaseModel):
    """Schema for salary range."""

    min: float = Field(..., gt=0, example=50000)
    max: float = Field(..., gt=0, example=80000)
    currency: str = Field(default="USD", example="USD")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class JobRequirementCreateSchema(BaseAppSchema):
    """Schema for creating a new job requirement."""

    title: str = Field(..., min_length=5, max_length=200, example="Senior Python Developer")
    department: str = Field(..., example="Engineering")
    description: str = Field(..., min_length=50, example="We are looking for a Senior Python Developer...")
    requirements: List[SkillRequirementSchema] = Field(..., example=[{"skill": "Python", "level": "advanced", "required": True}])
    experience: Optional[ExperienceSchema] = Field(default=None)
    location: Optional[str] = Field(default=None, example="New York, NY")
    job_type: Optional[str] = Field(default=None, enum=["full-time", "part-time", "contract", "internship"], example="full-time")
    salary_range: Optional[SalaryRangeSchema] = Field(default=None)
    benefits: Optional[List[str]] = Field(default=None, example=["Health Insurance", "401k", "Remote Work"])


class JobRequirementUpdateSchema(BaseAppSchema):
    """Schema for updating an existing job requirement."""

    title: Optional[str] = Field(default=None, min_length=5, max_length=200, example="Senior Python Developer")
    department: Optional[str] = Field(default=None, example="Engineering")
    description: Optional[str] = Field(default=None, min_length=50, example="Updated job description...")
    requirements: Optional[List[SkillRequirementSchema]] = Field(default=None)
    experience: Optional[ExperienceSchema] = Field(default=None)
    location: Optional[str] = Field(default=None, example="Remote")
    job_type: Optional[str] = Field(default=None, enum=["full-time", "part-time", "contract", "internship"])
    salary_range: Optional[SalaryRangeSchema] = Field(default=None)
    benefits: Optional[List[str]] = Field(default=None)
    status: Optional[JobRequirementStatus] = Field(default=None, example=JobRequirementStatus.ACTIVE)


class JobRequirementReadSchema(BaseAppSchema):
    """Schema for reading job requirement details."""

    job_requirement_id: UUID = Field(..., description="Job Requirement ID", example="b4c9f7c1-4d2c-5f7g-9b3e-0d9f8g7c6e5f")
    company_id: UUID = Field(..., description="Company ID", example="a3d8f6b0-3c1b-4e6f-8a2d-9c8e7f6a5b4d")
    title: str = Field(..., min_length=5, max_length=200, example="Senior Python Developer")
    department: str = Field(..., example="Engineering")
    description: str = Field(..., min_length=50, example="We are looking for a Senior Python Developer...")
    requirements: List[SkillRequirementSchema] = Field(...)
    experience: Optional[ExperienceSchema] = Field(default=None)
    location: Optional[str] = Field(default=None, example="New York, NY")
    job_type: Optional[str] = Field(default=None, example="full-time")
    salary_range: Optional[SalaryRangeSchema] = Field(default=None)
    benefits: Optional[List[str]] = Field(default=None)
    status: JobRequirementStatus = Field(default=JobRequirementStatus.DRAFT, example=JobRequirementStatus.ACTIVE)
    is_active: bool = Field(default=True, example=True)
    created_at: Optional[datetime] = Field(default=None, description="Created at", example="2023-01-01T12:00:00Z")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at", example="2023-01-02T14:30:00Z")


class JobRequirementListParamsSchema(BaseAppSchema):
    """Schema for job requirement list API parameters."""

    offset: int = Field(default=0, ge=0, description="Number of records to skip", example=0)
    limit: int = Field(default=20, ge=1, le=100, description="Number of items to return", example=10)
    order_by: str = Field(default="-created_at", description="Field to order by. Prefix with '-' for descending order", example="-title")
    search: Optional[str] = Field(default=None, description="Search query string to filter results", example="Python Developer")
    filters: Optional[List[str]] = Field(default=None, description="List of filter dicts as JSON strings", example=['{"field": "status", "operator": "eq", "value": "active"}'])
    status: Optional[JobRequirementStatus] = Field(default=None, example=JobRequirementStatus.ACTIVE)


class JobRequirementStatusUpdateSchema(BaseAppSchema):
    """Schema for updating job requirement status."""

    status: JobRequirementStatus = Field(..., description="Current status of the job requirement", example=JobRequirementStatus.ACTIVE)


# Rebuild models to resolve forward references
JobRequirementCreateSchema.model_rebuild()
JobRequirementUpdateSchema.model_rebuild()
JobRequirementReadSchema.model_rebuild()
