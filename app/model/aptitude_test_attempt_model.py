"""Aptitude Test Attempt Model - Stores candidate test attempts and results."""

import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class AptitudeTestAttemptModel(BaseAppModel):
    """Test attempt model - stores user attempts and results."""

    __tablename__ = "aptitude_test_attempts"

    attempt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aptitude_test_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # No FK - just reference
    job_requirement_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # No FK - just reference
    candidate_email = Column(String(255), nullable=False, index=True)
    candidate_name = Column(String(255), nullable=True)
    user_attempt = Column(Integer, nullable=False, default=1)  # Track attempt number for user

    # Test session info
    otp_code = Column(String(6), nullable=True)
    otp_verified = Column(Boolean, nullable=False, default=False)
    otp_verified_at = Column(String(50), nullable=True)
    
    # Test progress
    started_at = Column(String(50), nullable=True)
    submitted_at = Column(String(50), nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    
    # Answers and scoring
    answers = Column(JSONB, nullable=True)  # {"0": "A", "1": "C", "2": "B", ...}
    score = Column(Float, nullable=True)  # Score out of 100
    correct_answers_count = Column(Integer, nullable=True)
    total_questions_attempted = Column(Integer, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # Proctoring data
    tab_switches = Column(Integer, nullable=False, default=0)
    proctoring_violations = Column(JSONB, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending, in_progress, completed, expired
    
    # Override BaseAppModel audit fields for public endpoints
    created_by = Column(UUID(as_uuid=True), nullable=True)  # Nullable for public API
    updated_by = Column(UUID(as_uuid=True), nullable=True)

