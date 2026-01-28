"""Technical Interview Schemas."""

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

class TechnicalInterviewLoginRequest(BaseModel):
    """Schema for candidate login to technical interview."""
    job_requirement_id: UUID = Field(..., description="Job requirement ID")
    email: str = Field(..., description="Candidate email")
    password: str = Field(..., description="Candidate password")


class StartTechnicalInterviewRequest(BaseModel):
    """Schema for starting a technical interview session."""
    job_requirement_id: UUID = Field(..., description="Job requirement ID")
    candidate_id: UUID = Field(..., description="Candidate ID")


class UpdateInterviewScoresRequest(BaseModel):
    """Schema for updating interview scores after completion."""
    
    # Overall Scores
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    overall_rating: Optional[OverallRating] = None
    
    # Technical Knowledge Scores
    technical_knowledge_score: Optional[float] = Field(None, ge=0, le=100)
    domain_expertise_score: Optional[float] = Field(None, ge=0, le=100)
    coding_skills_score: Optional[float] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[float] = Field(None, ge=0, le=100)
    system_design_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Communication Scores
    communication_score: Optional[float] = Field(None, ge=0, le=100)
    articulation_score: Optional[float] = Field(None, ge=0, le=100)
    language_proficiency_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Behavioral Scores
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    composure_score: Optional[float] = Field(None, ge=0, le=100)
    enthusiasm_score: Optional[float] = Field(None, ge=0, le=100)
    professionalism_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Response Quality Scores
    response_relevance_score: Optional[float] = Field(None, ge=0, le=100)
    response_depth_score: Optional[float] = Field(None, ge=0, le=100)
    response_clarity_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Engagement Metrics
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    attentiveness_score: Optional[float] = Field(None, ge=0, le=100)


class CompleteInterviewRequest(BaseModel):
    """Schema for completing a technical interview with all results."""
    
    # Interview Duration
    interview_duration_seconds: int = Field(..., description="Total interview duration in seconds")
    
    # Overall Scores
    overall_score: float = Field(..., ge=0, le=100)
    overall_rating: OverallRating
    
    # Technical Knowledge Scores
    technical_knowledge_score: Optional[float] = Field(None, ge=0, le=100)
    domain_expertise_score: Optional[float] = Field(None, ge=0, le=100)
    coding_skills_score: Optional[float] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[float] = Field(None, ge=0, le=100)
    system_design_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Communication Scores
    communication_score: Optional[float] = Field(None, ge=0, le=100)
    articulation_score: Optional[float] = Field(None, ge=0, le=100)
    language_proficiency_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Behavioral Scores
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    composure_score: Optional[float] = Field(None, ge=0, le=100)
    enthusiasm_score: Optional[float] = Field(None, ge=0, le=100)
    professionalism_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Response Quality Scores
    response_relevance_score: Optional[float] = Field(None, ge=0, le=100)
    response_depth_score: Optional[float] = Field(None, ge=0, le=100)
    response_clarity_score: Optional[float] = Field(None, ge=0, le=100)
    
    # Question Statistics
    total_questions_asked: Optional[int] = None
    questions_answered: Optional[int] = None
    questions_skipped: Optional[int] = None
    questions_partially_answered: Optional[int] = None
    
    # Time Metrics
    average_response_time_seconds: Optional[float] = None
    total_speaking_time_seconds: Optional[float] = None
    total_silence_time_seconds: Optional[float] = None
    
    # Audio/Voice Analysis
    speech_rate_wpm: Optional[float] = None
    filler_words_count: Optional[int] = None
    interruptions_count: Optional[int] = None
    
    # Engagement Metrics
    engagement_score: Optional[float] = Field(None, ge=0, le=100)
    attentiveness_score: Optional[float] = Field(None, ge=0, le=100)
    follow_up_questions_asked: Optional[int] = None
    
    # Detailed JSON Data
    interview_transcript: Optional[List[Dict[str, Any]]] = None
    question_analysis: Optional[List[Dict[str, Any]]] = None
    skills_assessment: Optional[List[Dict[str, Any]]] = None
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
    
    # Proctoring/Monitoring Data
    tab_switches: Optional[int] = 0
    browser_focus_lost_count: Optional[int] = 0
    
    # Token Usage
    input_tokens_used: Optional[int] = None
    output_tokens_used: Optional[int] = None
    audio_input_seconds: Optional[float] = None
    audio_output_seconds: Optional[float] = None
    
    # Final Result
    result: str = Field(..., description="'pass' or 'fail'")
    passed_threshold: Optional[float] = Field(None, description="Threshold score used for pass/fail")


class SelectTopCandidatesRequest(BaseModel):
    """Schema for selecting top candidates based on technical interview scores."""
    job_requirement_id: UUID = Field(..., description="Job requirement ID")
    top_n: int = Field(..., gt=0, description="Number of top candidates to select")


# === Response Schemas ===

class TechnicalInterviewReadSchema(BaseModel):
    """Schema for reading technical interview data."""
    
    technical_interview_id: UUID
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
    
    # Technical Knowledge Scores
    technical_knowledge_score: Optional[float]
    domain_expertise_score: Optional[float]
    coding_skills_score: Optional[float]
    problem_solving_score: Optional[float]
    system_design_score: Optional[float]
    
    # Communication Scores
    communication_score: Optional[float]
    articulation_score: Optional[float]
    language_proficiency_score: Optional[float]
    
    # Behavioral Scores
    confidence_score: Optional[float]
    composure_score: Optional[float]
    enthusiasm_score: Optional[float]
    professionalism_score: Optional[float]
    
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
    attentiveness_score: Optional[float]
    
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


class TechnicalInterviewDetailedSchema(TechnicalInterviewReadSchema):
    """Schema for detailed technical interview data including transcript and analysis."""
    
    # Detailed JSON Data
    interview_transcript: Optional[List[Dict[str, Any]]]
    question_analysis: Optional[List[Dict[str, Any]]]
    skills_assessment: Optional[List[Dict[str, Any]]]
    
    # All time metrics
    longest_response_time_seconds: Optional[float]
    shortest_response_time_seconds: Optional[float]
    total_silence_time_seconds: Optional[float]
    
    # Audio/Voice Analysis
    speech_rate_wpm: Optional[float]
    voice_clarity_score: Optional[float]
    filler_words_count: Optional[int]
    interruptions_count: Optional[int]
    
    # Proctoring Data
    tab_switches: Optional[int]
    browser_focus_lost_count: Optional[int]
    suspicious_activity_flags: Optional[List[Dict[str, Any]]]
    
    # Technical Metadata
    audio_quality_score: Optional[float]
    video_enabled: Optional[bool]
    connection_quality: Optional[str]
    technical_issues: Optional[List[Dict[str, Any]]]
    
    # Token Usage
    input_tokens_used: Optional[int]
    output_tokens_used: Optional[int]
    audio_input_seconds: Optional[float]
    audio_output_seconds: Optional[float]
    
    # Additional
    ai_recommendation_reason: Optional[str]
    interviewer_notes: Optional[str]
    candidate_feedback: Optional[str]
    languages_used: Optional[List[str]]
    ai_model_used: Optional[str]


class InterviewSessionResponse(BaseModel):
    """Response schema for interview session creation."""
    technical_interview_id: UUID
    job_requirement_id: UUID
    candidate_id: UUID
    interview_session_id: str
    interview_status: str
    websocket_url: str
    job_details: Dict[str, Any]
    candidate_info: Dict[str, Any]


class CandidateInterviewResult(BaseModel):
    """Schema for candidate interview result in selection."""
    candidate_id: UUID
    candidate_email: str
    candidate_name: str
    overall_score: float
    technical_knowledge_score: Optional[float]
    communication_score: Optional[float]
    confidence_score: Optional[float]
    ai_recommendation: Optional[str]
    result: str
    rank: int

    class Config:
        from_attributes = True
