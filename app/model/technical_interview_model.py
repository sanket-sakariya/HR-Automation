"""Technical Interview Model - Stores comprehensive interview results and evaluation metrics."""

import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.model.baseapp_model import BaseAppModel


class TechnicalInterviewModel(BaseAppModel):
    """
    Comprehensive Technical Interview model.
    Stores all details from AI-conducted technical interviews for candidate evaluation.
    """

    __tablename__ = "technical_interviews"

    # Primary identifiers
    technical_interview_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    
    # Technical Knowledge Scores
    technical_knowledge_score = Column(Float, nullable=True)  # Understanding of technical concepts
    domain_expertise_score = Column(Float, nullable=True)  # Knowledge specific to job domain
    
    # Communication Scores
    communication_score = Column(Float, nullable=True)  # Overall communication effectiveness
    language_proficiency_score = Column(Float, nullable=True)  # Grammar, vocabulary, fluency
    
    # Behavioral Scores
    confidence_score = Column(Float, nullable=True)  # Confidence level during interview
    professionalism_score = Column(Float, nullable=True)  # Professional demeanor
    
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
    #   "question_category": "technical/behavioral/situational",
    #   "difficulty": "easy/medium/hard",
    #   "response_text": "...",
    #   "response_time_seconds": 5.2,
    #   "response_score": 85,
    #   "keywords_expected": ["java", "spring"],
    #   "keywords_mentioned": ["java"],
    #   "feedback": "Good understanding but missed spring framework details"
    # }]
    
    # Skill Assessment
    skills_assessment = Column(JSONB, nullable=True)
    # Format: [{
    #   "skill_name": "Java",
    #   "skill_category": "programming",
    #   "proficiency_level": "advanced/intermediate/beginner",
    #   "score": 85,
    #   "evidence": "Demonstrated knowledge of multithreading and collections"
    # }]
    
    # Strengths and Weaknesses
    candidate_strengths = Column(JSONB, nullable=True)  # ["strong problem solving", "good communication"]
    candidate_weaknesses = Column(JSONB, nullable=True)  # ["needs work on system design", "nervous initially"]
    
    # AI Recommendations
    ai_recommendation = Column(String(50), nullable=True)  # strongly_recommend, recommend, neutral, not_recommend
    ai_recommendation_reason = Column(Text, nullable=True)  # Detailed recommendation explanation
    ai_feedback_summary = Column(Text, nullable=True)  # Overall feedback summary
    
    # Areas for Improvement
    improvement_areas = Column(JSONB, nullable=True)  # ["system design", "communication"]
    
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
