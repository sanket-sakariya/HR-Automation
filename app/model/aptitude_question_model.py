"""Aptitude Question Model - Stores individual test questions."""

import uuid
from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class AptitudeQuestionModel(BaseAppModel):
    """Aptitude question model - stores individual questions."""

    __tablename__ = "aptitude_questions"

    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aptitude_test_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # No FK - just reference
    question_number = Column(Integer, nullable=False)
    difficulty = Column(String(20), nullable=False)  # simple, medium, hard
    category = Column(String(50), nullable=False)  # core_logic, critical_thinking, domain_specific
    question_text = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False)  # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer = Column(String(1), nullable=False)  # A, B, C, or D
    explanation = Column(Text, nullable=True)
    time_allocated_seconds = Column(Integer, nullable=False, default=90)
    tags = Column(JSONB, nullable=True)  # Array of tags
    
    # Override BaseAppModel audit fields for public endpoints
    created_by = Column(UUID(as_uuid=True), nullable=True)  # Nullable for public API
    updated_by = Column(UUID(as_uuid=True), nullable=True)

