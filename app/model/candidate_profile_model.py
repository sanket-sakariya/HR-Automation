import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class CandidateProfileModel(BaseAppModel):
    """Candidate profile model for work experience and education data."""

    __tablename__ = "candidate_profiles"

    candidate_profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    profile_type = Column(String(20), nullable=False)  # 'work_experience' or 'education'

    # Work Experience fields
    company = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    current = Column(Boolean, nullable=True)
    description = Column(Text, nullable=True)
    skills = Column(JSONB, nullable=True)  # Array of skill strings

    # Education fields
    institution = Column(String(255), nullable=True)
    degree = Column(String(255), nullable=True)
    field_of_study = Column(String(255), nullable=True)
    grade = Column(String(50), nullable=True)

    # Shared date fields
    position_start_date = Column(DateTime(timezone=True), nullable=True)
    position_end_date = Column(DateTime(timezone=True), nullable=True)
    education_start_date = Column(DateTime(timezone=True), nullable=True)
    education_end_date = Column(DateTime(timezone=True), nullable=True)
