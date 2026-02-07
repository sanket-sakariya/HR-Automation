"""HR Interview Schemas."""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class InterviewStatus(str, Enum):
    """Interview status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    EXPIRED = "expired"


class OverallRating(str, Enum):
    """Overall rating enumeration."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    POOR = "poor"


class AIRecommendation(str, Enum):
    """AI recommendation enumeration."""
    STRONGLY_RECOMMEND = "strongly_recommend"
    RECOMMEND = "recommend"
    NEUTRAL = "neutral"
    NOT_RECOMMEND = "not_recommend"


# === Request Schemas ===

class HRInterviewLoginRequest(BaseModel):
    """Schema for candidate login to HR interview."""
    job_requirement_id: UUID = Field(..., description="Job requirement ID")
    email: str = Field(..., description="Candidate email")
    password: str = Field(..., description="Candidate password")


class StartHRInterviewRequest(BaseModel):
    """Schema for starting an HR interview session."""
    job_requirement_id: UUID = Field(..., description="Job requirement ID")
    candidate_id: UUID = Field(..., description="Candidate ID")


class UpdateInterviewScoresRequest(BaseModel):
    """Schema for updating interview scores after completion."""
    
    # Overall Scores
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    overall_rating: Optional[OverallRating] = None
    
    # Communication Scores
    communication_score: Optional[float] = Field(None, ge=0, le=100)
    language_proficiency_score: Optional[float] = Field(None, ge=0, le=100)
    articulation_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Behavioral Scores
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    professionalism_score: Optional[float] = Field(None, ge=0, le=100)
    attitude_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Soft Skills Scores
    teamwork_score: Optional[float] = Field(None, ge=0, le=100)
    leadership_score: Optional[float] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[float] = Field(None, ge=0, le=100)
    adaptability_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Cultural Fit Scores
    cultural_fit_score: Optional[float] = Field(None, ge=0, le=100)
    motivation_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Response Quality Scores
    response_relevance_score: Optional[float] = Field(None, ge=0, le=100)
    response_depth_score: Optional[float] = Field(None, ge=0, le=100)
    response_clarity_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Engagement Metrics
    engagement_score: Optional[float] = Field(None, ge=0, le=100)


class CompleteHRInterviewRequest(BaseModel):
    """Schema for completing an HR interview with all results."""
    
    # Interview Duration
    interview_duration_seconds: int = Field(..., description="Total interview duration in seconds")
    
    # Overall Scores
    overall_score: float = Field(..., ge=0, le=100)
    overall_rating: OverallRating
    
    # Communication Scores
    communication_score: Optional[float] = Field(None, ge=0, le=100)
    language_proficiency_score: Optional[float] = Field(None, ge=0, le=100)
    articulation_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Behavioral Scores
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    professionalism_score: Optional[float] = Field(None, ge=0, le=100)
    attitude_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Soft Skills Scores
    teamwork_score: Optional[float] = Field(None, ge=0, le=100)
    leadership_score: Optional[float] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[float] = Field(None, ge=0, le=100)
    adaptability_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Cultural Fit Scores
    cultural_fit_score: Optional[float] = Field(None, ge=0, le=100)
    motivation_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Response Quality Scores
    response_relevance_score: Optional[float] = Field(None, ge=0, le=100)
    response_depth_score: Optional[float] = Field(None, ge=0, le=100)
    response_clarity_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Question Statistics
    total_questions_asked: Optional[int] = None
    questions_answered: Optional[int] = None
    questions_skipped: Optional[int] = None
    
    # Time Metrics
    average_response_time_seconds: Optional[float] = None
    total_speaking_time_seconds: Optional[float] = None
    
    # Engagement Metrics
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    follow_up_questions_asked: Optional[int] = None
    
    # Detailed JSON Data
    interview_transcript: Optional[List[Dict[str, Any]]] = None
    question_analysis: Optional[List[Dict[str, Any]]] = None
    soft_skills_assessment: Optional[List[Dict[str, Any]]] = None
    candidate_strengths: Optional[List[str]] = None
    candidate_weaknesses: Optional[List[str]] = None
    
    # AI Recommendations
    ai_recommendation: Optional[AIRecommendation] = None
    ai_recommendation_reason: Optional[str] = None
    ai_feedback_summary: Optional[str] = None
    improvement_areas: Optional[List[str]] = None
    
    # Interview Metadata
    interview_language: Optional[str] = None
    languages_used: Optional[List[str]] = None
    
    # Token Usage
    input_tokens_used: Optional[int] = None
    output_tokens_used: Optional[int] = None
    audio_input_seconds: Optional[float] = None
    audio_output_seconds: Optional[float] = None
    
    # Final Result
    result: str = Field(..., description="'pass' or 'fail'")
    passed_threshold: Optional[float] = Field(None, description="Threshold score used for pass/fail")


class SelectTopCandidatesRequest(BaseModel):
    """Schema for selecting top candidates based on HR interview scores."""
    job_requirement_id: UUID = Field(..., description="Job requirement ID")
    top_n: int = Field(..., gt=0, description="Number of top candidates to select")


# === Response Schemas ===

class HRInterviewReadSchema(BaseModel):
    """Schema for reading HR interview data."""
    
    hr_interview_id: UUID
    job_requirement_id: UUID
    candidate_id: UUID
    
    # Interview Session Details
    interview_session_id: Optional[str]
    interview_started_at: Optional[datetime]
    interview_ended_at: Optional[datetime]
    interview_duration_seconds: Optional[int]
    interview_status: str
    
    # Overall Scores
    overall_score: Optional[float]
    overall_rating: Optional[str]
    
    # Communication Scores
    communication_score: Optional[float]
    language_proficiency_score: Optional[float]
    articulation_score: Optional[float]
    
    # Behavioral Scores
    confidence_score: Optional[float]
    professionalism_score: Optional[float]
    attitude_score: Optional[float]
    
    # Soft Skills Scores
    teamwork_score: Optional[float]
    leadership_score: Optional[float]
    problem_solving_score: Optional[float]
    adaptability_score: Optional[float]
    
    # Cultural Fit Scores
    cultural_fit_score: Optional[float]
    motivation_score: Optional[float]
    
    # Response Quality Scores
    response_relevance_score: Optional[float]
    response_depth_score: Optional[float]
    response_clarity_score: Optional[float]
    
    # Question Statistics
    total_questions_asked: Optional[int]
    questions_answered: Optional[int]
    questions_skipped: Optional[int]
    
    # Time Metrics
    average_response_time_seconds: Optional[float]
    total_speaking_time_seconds: Optional[float]
    
    # Engagement Metrics
    engagement_score: Optional[float]
    
    # AI Recommendations
    ai_recommendation: Optional[str]
    ai_feedback_summary: Optional[str]
    candidate_strengths: Optional[List[str]]
    candidate_weaknesses: Optional[List[str]]
    improvement_areas: Optional[List[str]]
    
    # Final Result
    result: Optional[str]
    passed_threshold: Optional[float]
    
    # Metadata
    interview_language: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class HRInterviewDetailedSchema(HRInterviewReadSchema):
    """Schema for detailed HR interview data including transcript and analysis."""
    
    # Detailed JSON Data
    interview_transcript: Optional[List[Dict[str, Any]]]
    question_analysis: Optional[List[Dict[str, Any]]]
    soft_skills_assessment: Optional[List[Dict[str, Any]]]
    
    # All time metrics
    longest_response_time_seconds: Optional[float]
    shortest_response_time_seconds: Optional[float]
    
    # Technical Metadata
    video_enabled: Optional[bool]
    
    # Token Usage
    input_tokens_used: Optional[int]
    output_tokens_used: Optional[int]
    audio_input_seconds: Optional[float]
    audio_output_seconds: Optional[float]
    
    # Additional
    ai_recommendation_reason: Optional[str]
    languages_used: Optional[List[str]]
    ai_model_used: Optional[str]


class HRInterviewSessionResponse(BaseModel):
    """Response schema for interview session creation."""
    hr_interview_id: UUID
    job_requirement_id: UUID
    candidate_id: UUID
    interview_session_id: str
    interview_status: str
    websocket_url: str
    job_details: Dict[str, Any]
    candidate_info: Dict[str, Any]


class CandidateHRInterviewResult(BaseModel):
    """Schema for candidate interview result in selection."""
    candidate_id: UUID
    candidate_email: str
    candidate_name: str
    overall_score: float
    communication_score: Optional[float]
    confidence_score: Optional[float]
    cultural_fit_score: Optional[float]
    teamwork_score: Optional[float]
    ai_recommendation: Optional[str]
    result: str
    rank: int

    class Config:
        from_attributes = True
