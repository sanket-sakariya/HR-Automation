import uuid
from sqlalchemy import Column, String, Float, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class CandidateModel(BaseAppModel):
    """Candidate model for job applications - simplified for public forms."""

    __tablename__ = "candidates"

    candidate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_requirement_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    first_name = Column(String(50), nullable=False, info={"search": True}, index=True)
    last_name = Column(String(50), nullable=False, info={"search": True}, index=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    current_location = Column(String(255), nullable=True)
    willing_to_relocate = Column(Boolean, nullable=True, default=False)
    skills = Column(JSONB, nullable=True)  # Array of skill strings
    expected_salary = Column(Float, nullable=True)
    notice_period = Column(String(100), nullable=True)
    resume_url = Column(String(500), nullable=True)  # Full file path to stored resume
    candidate_resume_score = Column(Float, nullable=True)  # AI-generated resume score
    status = Column(String(20), nullable=False, default="active")  # active, inactive

    # Unique constraint to prevent same candidate from applying to same job multiple times
    __table_args__ = (
        Index('unique_candidate_job', candidate_id, job_requirement_id, email, phone, unique=True),
    )
