"""HR Interview Model - Stores comprehensive HR interview results and evaluation metrics."""

import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class HRInterviewModel(BaseAppModel):
    """
    Comprehensive HR Interview model.
    Stores all details from AI-conducted HR interviews for candidate evaluation.
    """

    __tablename__ = "hr_interviews"

    # Primary identifiers
    hr_interview_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_requirement_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Interview Session Details
    interview_session_id = Column(String(100), nullable=True)  # Unique session identifier
    interview_started_at = Column(DateTime(timezone=True), nullable=True)
    interview_ended_at = Column(DateTime(timezone=True), nullable=True)
    interview_duration_seconds = Column(Integer, nullable=True)  # Total interview duration
    
    # Interview Status
    interview_status = Column(String(20), nullable=False, default="pending")  # pending, in_progress, completed, interrupted, expired
    
    # === SCORING METRICS (0-100 scale) ===
    
    # Overall Scores
    overall_score = Column(Float, nullable=True)  # Weighted average of all scores
    overall_rating = Column(String(20), nullable=True)  # excellent, good, average, below_average, poor
    
    # Communication Scores
    communication_score = Column(Float, nullable=True)  # Overall communication effectiveness
    language_proficiency_score = Column(Float, nullable=True)  # Grammar, vocabulary, fluency
    articulation_score = Column(Float, nullable=True)  # Clarity and coherence of speech
    
    # Behavioral Scores
    confidence_score = Column(Float, nullable=True)  # Confidence level during interview
    professionalism_score = Column(Float, nullable=True)  # Professional demeanor
    attitude_score = Column(Float, nullable=True)  # Positive attitude and enthusiasm
    
    # Soft Skills Scores
    teamwork_score = Column(Float, nullable=True)  # Team collaboration ability
    leadership_score = Column(Float, nullable=True)  # Leadership potential
    problem_solving_score = Column(Float, nullable=True)  # Problem-solving approach
    adaptability_score = Column(Float, nullable=True)  # Adaptability to change
    
    # Cultural Fit Scores
    cultural_fit_score = Column(Float, nullable=True)  # Alignment with company culture
    motivation_score = Column(Float, nullable=True)  # Motivation and career goals alignment
    
    # Response Quality Scores
    response_relevance_score = Column(Float, nullable=True)  # How relevant answers were to questions
    response_depth_score = Column(Float, nullable=True)  # Depth and detail of answers
    response_clarity_score = Column(Float, nullable=True)  # Clarity of responses
    
    # === DETAILED METRICS ===
    
    # Question Statistics
    total_questions_asked = Column(Integer, nullable=True)
    questions_answered = Column(Integer, nullable=True)
    questions_skipped = Column(Integer, nullable=True)
    
    # Time Metrics
    average_response_time_seconds = Column(Float, nullable=True)  # Average time to start responding
    longest_response_time_seconds = Column(Float, nullable=True)  # Longest pause before answering
    shortest_response_time_seconds = Column(Float, nullable=True)  # Quickest response
    total_speaking_time_seconds = Column(Float, nullable=True)  # Total time candidate spoke
    
    # Engagement Metrics
    engagement_score = Column(Float, nullable=True)  # Overall engagement level
    follow_up_questions_asked = Column(Integer, nullable=True)  # Questions candidate asked
    
    # === DETAILED JSON DATA ===
    
    # Interview Transcript
    interview_transcript = Column(JSONB, nullable=True)
    # Format: [{"timestamp": "00:01:23", "speaker": "ai/candidate", "text": "...", "sentiment": "positive/neutral/negative"}]
    
    # Question-wise Analysis
    question_analysis = Column(JSONB, nullable=True)
    # Format: [{
    #   "question_number": 1,
    #   "question_text": "...",
    #   "question_category": "behavioral/situational/cultural/career",
    #   "difficulty": "easy/medium/hard",
    #   "response_text": "...",
    #   "response_time_seconds": 5.2,
    #   "response_score": 85,
    #   "keywords_expected": ["teamwork", "collaboration"],
    #   "keywords_mentioned": ["teamwork"],
    #   "feedback": "Good example but could elaborate more on outcomes"
    # }]
    
    # Soft Skills Assessment
    soft_skills_assessment = Column(JSONB, nullable=True)
    # Format: [{
    #   "skill_name": "Communication",
    #   "skill_category": "interpersonal",
    #   "proficiency_level": "advanced/intermediate/beginner",
    #   "score": 85,
    #   "evidence": "Demonstrated clear articulation and active listening"
    # }]
    
    # Strengths and Weaknesses
    candidate_strengths = Column(JSONB, nullable=True)  # ["strong communication", "positive attitude"]
    candidate_weaknesses = Column(JSONB, nullable=True)  # ["needs work on leadership examples", "nervous initially"]
    
    # AI Recommendations
    ai_recommendation = Column(String(50), nullable=True)  # strongly_recommend, recommend, neutral, not_recommend
    ai_recommendation_reason = Column(Text, nullable=True)  # Detailed recommendation explanation
    ai_feedback_summary = Column(Text, nullable=True)  # Overall feedback summary
    
    # Areas for Improvement
    improvement_areas = Column(JSONB, nullable=True)  # ["leadership skills", "conflict resolution examples"]
    
    # Interview Metadata
    interview_language = Column(String(50), nullable=True)  # Primary language used (English, Hindi, Gujarati)
    languages_used = Column(JSONB, nullable=True)  # ["English", "Hindi"] - all languages used
    ai_model_used = Column(String(100), nullable=True)  # gemini-2.5-flash-native-audio
    
    # Technical Metadata
    video_enabled = Column(Boolean, nullable=True, default=False)
    
    # Token Usage (for cost tracking)
    input_tokens_used = Column(Integer, nullable=True)
    output_tokens_used = Column(Integer, nullable=True)
    audio_input_seconds = Column(Float, nullable=True)
    audio_output_seconds = Column(Float, nullable=True)
    
    # Final Result
    result = Column(String(10), nullable=True)  # 'pass' or 'fail'
    passed_threshold = Column(Float, nullable=True)  # The threshold score used for pass/fail
