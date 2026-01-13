"""Aptitude Test Model - Stores generated tests."""

import uuid
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class AptitudeTestModel(BaseAppModel):
    """Aptitude test model - stores generated tests."""

    __tablename__ = "aptitude_tests"

    aptitude_test_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_requirement_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # No FK - just reference
    test_title = Column(String(255), nullable=False)
    total_questions = Column(Integer, nullable=False, default=30)
    total_time_minutes = Column(Integer, nullable=False, default=45)
    passing_score_percentage = Column(Integer, nullable=False, default=60)
    test_metadata = Column(JSONB, nullable=True)  # Store test configuration
    proctoring_settings = Column(JSONB, nullable=True)  # Proctoring configuration
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Override BaseAppModel audit fields for public endpoints
    created_by = Column(UUID(as_uuid=True), nullable=True)  # Nullable for public API
    updated_by = Column(UUID(as_uuid=True), nullable=True)
