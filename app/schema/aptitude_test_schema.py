"""Aptitude Test Schemas."""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# Question Schemas
class AptitudeQuestionCreate(BaseModel):
    """Schema for creating a question."""
    question_number: int
    difficulty: str
    category: str
    question_text: str
    options: Dict[str, str]  # {"A": "...", "B": "...", ...}
    correct_answer: str
    explanation: Optional[str] = None
    time_allocated_seconds: int = 90
    tags: Optional[List[str]] = None


class AptitudeQuestionRead(BaseModel):
    """Schema for reading a question (public - without correct answer)."""
    question_id: UUID
    question_number: int
    difficulty: str
    category: str
    question_text: str
    options: Dict[str, str]
    time_allocated_seconds: int
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class AptitudeQuestionWithAnswer(AptitudeQuestionRead):
    """Schema for reading a question with correct answer (private)."""
    correct_answer: str
    explanation: Optional[str] = None


# Test Schemas
class AptitudeTestCreate(BaseModel):
    """Schema for creating a test."""
    job_requirement_id: UUID
    test_title: Optional[str] = None
    total_questions: int = 30
    total_time_minutes: int = 45
    passing_score_percentage: int = 60
    test_metadata: Optional[Dict[str, Any]] = None
    proctoring_settings: Optional[Dict[str, Any]] = None


class AptitudeTestRead(BaseModel):
    """Schema for reading a test."""
    aptitude_test_id: UUID
    job_requirement_id: UUID
    test_title: str
    total_questions: int
    total_time_minutes: int
    passing_score_percentage: int
    test_metadata: Optional[Dict[str, Any]] = None
    proctoring_settings: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AptitudeTestWithQuestions(AptitudeTestRead):
    """Schema for test with questions (without answers)."""
    questions: List[AptitudeQuestionRead]


# Test Attempt Schemas
class TestAttemptStart(BaseModel):
    """Schema for starting a test attempt."""
    candidate_email: EmailStr
    candidate_name: Optional[str] = None


class TestAttemptVerifyOTP(BaseModel):
    """Schema for verifying OTP."""
    attempt_id: UUID
    otp_code: str


class TestAnswerSubmit(BaseModel):
    """Schema for submitting test answers."""
    attempt_id: UUID
    answers: Dict[int, str]  # {0: "A", 1: "C", ...}
    time_taken_seconds: int
    tab_switches: int = 0


class TestAttemptResult(BaseModel):
    """Schema for test results."""
    attempt_id: UUID
    candidate_email: str
    candidate_name: Optional[str]
    score: float
    correct_answers_count: int
    total_questions_attempted: int
    total_questions: int
    passed: bool
    time_taken_seconds: int
    submitted_at: Optional[str]

    class Config:
        from_attributes = True


# Response Schemas
class TestCreatedResponse(BaseModel):
    """Response after test creation."""
    aptitude_test_id: UUID
    job_requirement_id: UUID
    test_title: str
    total_questions: int
    questions_generated: int
    public_url: str


class TestAccessResponse(BaseModel):
    """Response for test access (after OTP verification)."""
    test: AptitudeTestWithQuestions
    attempt_id: UUID
    time_remaining_seconds: int


class OTPSentResponse(BaseModel):
    """Response after OTP is sent."""
    attempt_id: UUID
    message: str
    email: str
    expires_in_minutes: int = 10

