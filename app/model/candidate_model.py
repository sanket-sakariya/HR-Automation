import uuid
from sqlalchemy import Column, String, Float, Boolean, Text, Index, Numeric
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
    password = Column(String(255), nullable=False)  # 8-character random password
    phone = Column(String(20), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    current_location = Column(String(255), nullable=True)
    willing_to_relocate = Column(Boolean, nullable=True, default=False)
    skills = Column(JSONB, nullable=True)  # Array of skill strings
    expected_salary = Column(Float, nullable=True)
    notice_period = Column(String(100), nullable=True)
    resume_url = Column(String(500), nullable=True)  # Full file path to stored resume
    candidate_resume_score = Column(Numeric(10, 4), nullable=True)  # AI-generated resume score
    status = Column(String(20), nullable=False, default="active")  # active, inactive

    # Test tracking fields - indicates if candidate has taken the test
    aptitude_test = Column(Boolean, nullable=True, default=False)  # Has taken aptitude test
    technical_test = Column(Boolean, nullable=True, default=False)  # Has taken technical test
    hr_test = Column(Boolean, nullable=True, default=False)  # Has taken HR test

    # Test result fields - pass/fail status
    aptitude_test_result = Column(String(10), nullable=True)  # 'pass' or 'fail'
    technical_test_result = Column(String(10), nullable=True)  # 'pass' or 'fail'
    hr_test_result = Column(String(10), nullable=True)  # 'pass' or 'fail'

    # Resume selection field - based on top N resume scores for the job
    resume_selected = Column(Boolean, nullable=True, default=False)  # True if resume is selected

    # Unique constraint to prevent same candidate from applying to same job multiple times
    __table_args__ = (
        Index('unique_candidate_job', candidate_id, job_requirement_id, email, phone, unique=True),
    )
