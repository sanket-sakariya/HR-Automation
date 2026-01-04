import uuid
from sqlalchemy import Column, String, Integer, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class JobRequirementModel(BaseAppModel):
    """Job requirement model for company hiring requirements."""

    __tablename__ = "job_requirements"

    job_requirement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(200), nullable=False, info={"search": True}, index=True)
    department = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(JSONB, nullable=False)  # Array of requirement objects: [{skill, level, required}]
    experience = Column(JSONB, nullable=True)  # {minYears, maxYears, preferred}
    location = Column(String(255), nullable=True)
    job_type = Column(String(20), nullable=True)  # full-time, part-time, contract, internship
    salary_range = Column(JSONB, nullable=True)  # {min, max, currency}
    benefits = Column(JSONB, nullable=True)  # Array of benefit strings
    status = Column(String(20), nullable=False, default="draft")  # draft, active, closed
