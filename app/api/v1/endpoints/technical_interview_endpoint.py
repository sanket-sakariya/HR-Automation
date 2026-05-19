"""Technical Interview Endpoints - Complete interview management API."""

from __future__ import annotations
from typing import Optional
from uuid import UUID
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db
from app.config.constants import SuccessMessages

from app.schema.response_schema import ApiResponseSchema
from app.schema.technical_interview_schema import (
    TechnicalInterviewStartRequest,
    CompleteInterviewRequest,
)

from app.service.technical_interview_service import TechnicalInterviewService
from app.repository.technical_interview_repository import TechnicalInterviewRepository
from app.repository.candidate_repository import CandidateRepository
from app.repository.job_requirement_repository import JobRequirementRepository

# Technical interview service URL
TECHNICAL_INTERVIEW_SERVICE_URL = "http://localhost:8100"

router = APIRouter(
    prefix="/technical-interview",
    tags=["Technical Interview Management"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


@router.post("/login", response_model=ApiResponseSchema[dict])
async def login_and_lookup_candidate(
    login_data: dict,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Resolve a candidate from just email + password.

    Used by the technical-interview microservice's simplified login screen so the
    candidate does NOT need to know/enter their candidate_id or job_requirement_id.
    Returns the candidate_id and job_requirement_id which the caller can then pass
    to /technical-interview/start/{candidate_id}.
    """
    email = (login_data or {}).get("email")
    password = (login_data or {}).get("password")

    if not email or not password:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    candidate_repo = CandidateRepository(db)
    candidate = await candidate_repo.get_by_email(email)
    if not candidate:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if candidate.password != password:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not candidate.aptitude_test or candidate.aptitude_test_result != "pass":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="You must pass the aptitude test before taking the technical interview.",
        )

    if candidate.technical_test and candidate.technical_test_result:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"You have already completed the technical interview (result: {candidate.technical_test_result}).",
        )

    return ApiResponseSchema(
        success=True,
        message="Credentials verified",
        data={
            "candidate_id": str(candidate.candidate_id),
            "job_requirement_id": str(candidate.job_requirement_id),
            "candidate_name": f"{candidate.first_name or ''} {candidate.last_name or ''}".strip(),
            "candidate_email": candidate.email,
        },
    )


@router.post("/reset/{candidate_id}", response_model=ApiResponseSchema[dict])
async def reset_candidate_technical_interview(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset technical interview attempts for a candidate so they can retake it.

    Deletes existing technical_interviews rows for this candidate and clears
    the technical_test / technical_test_result / technical_test_score fields
    on the candidate so the "Schedule Technical Interview" flow re-opens.
    """
    from sqlalchemy import delete as sa_delete
    from app.model.technical_interview_model import TechnicalInterviewModel

    try:
        candidate_repo = CandidateRepository(db)
        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}",
            )

        # Hard-delete prior technical interview rows for this candidate.
        result = await db.execute(
            sa_delete(TechnicalInterviewModel).where(
                TechnicalInterviewModel.candidate_id == candidate_id
            )
        )
        deleted = getattr(result, "rowcount", 0) or 0

        # Clear flags so candidate re-enters the technical-interview-eligible pool.
        candidate.technical_test = False
        candidate.technical_test_result = None
        try:
            candidate.technical_test_score = None
        except Exception:
            pass

        await db.commit()
        await db.refresh(candidate)

        return ApiResponseSchema(
            success=True,
            message=(
                f"Reset complete — {deleted} previous technical interview(s) cleared. "
                "Candidate can be scheduled for a fresh technical interview."
            ),
            data={
                "candidate_id": str(candidate_id),
                "email": candidate.email,
                "deleted_interviews": deleted,
                "job_requirement_id": str(candidate.job_requirement_id),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset technical interview: {str(e)}",
        )


@router.post("/start/{candidate_id}", response_model=ApiResponseSchema[dict])
async def start_technical_interview(
    candidate_id: UUID,
    payload: TechnicalInterviewStartRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Start Technical Interview for a Candidate.
    
    Flow:
    1. Verify candidate exists and job requirement matches
    2. Check if candidate passed aptitude test
    3. Get candidate details including resume
    4. Generate master AI prompt based on job requirements and candidate profile
    5. Create interview session
    6. Return interview URL and details
    
    Interview Duration: Minimum 5 minutes, Maximum 15 minutes
    
    Request Body:
    - job_requirement_id: UUID of the job requirement
    
    No email/password required - interview starts directly.
    """
    try:
        service = TechnicalInterviewService(db)
        candidate_repo = CandidateRepository(db)
        job_repo = JobRequirementRepository(db)
        
        # Step 1: Get candidate by ID
        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}"
            )
        
        # Step 2: Verify job requirement matches
        if str(candidate.job_requirement_id) != str(payload.job_requirement_id):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Job requirement does not match candidate's application"
            )
        
        # Step 3: Check if candidate passed aptitude test
        if not candidate.aptitude_test or candidate.aptitude_test_result != "pass":
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Candidate must pass aptitude test before technical interview"
            )
        
        # Step 4: Check if candidate has already taken technical test
        if candidate.technical_test and candidate.technical_test_result:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Candidate has already completed technical interview with result: {candidate.technical_test_result}"
            )
        
        # Step 5: Get job details
        job = await job_repo.get_by_id(candidate.job_requirement_id)
        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Job requirement not found"
            )
        
        # Step 6: Extract resume text if available
        resume_text = None
        if candidate.resume_url:
            resume_path = Path(candidate.resume_url)
            if resume_path.exists():
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(resume_path))
                    resume_text = ""
                    for page in reader.pages:
                        resume_text += page.extract_text() + "\n"
                except Exception as e:
                    print(f"Warning: Could not extract resume text: {e}")
        
        # Step 7: Create interview session
        session_result = await service.create_interview_session(
            candidate_id=candidate_id,
            job_requirement_id=candidate.job_requirement_id
        )
        
        if "error" in session_result:
            if session_result.get("already_completed"):
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=session_result["error"]
                )
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=session_result["error"]
            )
        
        interview = session_result["interview"]
        job_details = session_result["job_details"]
        candidate_info = session_result["candidate_info"]
        
        # Step 8: Generate master AI prompt with job details, candidate info, and resume
        system_instruction = service.generate_master_prompt(
            job_details=job_details,
            candidate_info=candidate_info,
            resume_text=resume_text
        )
        
        # WebSocket URL for the interview (pointing to the technical-interview-service on port 8100)
        websocket_url = f"ws://localhost:8100/ws/interview/{interview.interview_session_id}"
        interview_url = f"http://localhost:8100/interview/{interview.interview_session_id}"
        
        # Step 9: Register the session with the technical-interview-service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                register_response = await client.post(
                    f"{TECHNICAL_INTERVIEW_SERVICE_URL}/register-session",
                    json={
                        "session_id": interview.interview_session_id,
                        "job_details": job_details,
                        "candidate_info": candidate_info,
                        "system_instruction": system_instruction,
                        "technical_interview_id": str(interview.technical_interview_id)
                    }
                )
                if register_response.status_code != 200:
                    print(f"Warning: Could not register session with technical-interview-service: {register_response.text}")
        except Exception as e:
            print(f"Warning: Could not connect to technical-interview-service: {e}")
            # Continue anyway - the session might need to be registered manually
        
        return ApiResponseSchema(
            success=True,
            message="Technical interview started successfully. Interview duration: 5-15 minutes.",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "is_existing_session": session_result.get("is_existing", False),
                "websocket_url": websocket_url,
                "interview_url": interview_url,
                "job_details": job_details,
                "candidate_info": candidate_info,
                "system_instruction": system_instruction,
                "interview_config": {
                    "min_duration_minutes": 5,
                    "max_duration_minutes": 15,
                    "auto_end_after_minutes": 15
                },
                "instructions": {
                    "1": "Open the interview_url in your browser",
                    "2": "Allow microphone and camera permissions",
                    "3": "Click 'Start Interview' to begin",
                    "4": "Speak clearly - the AI supports English, Hindi, and Gujarati",
                    "5": "Interview will last between 5-15 minutes"
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start technical interview: {str(e)}"
        )


@router.post("/complete/{technical_interview_id}", response_model=ApiResponseSchema[dict])
async def complete_interview(
    technical_interview_id: UUID,
    payload: CompleteInterviewRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Complete the technical interview with all scores and analysis.
    This endpoint is called by the AI interview system after the interview ends.
    
    Stores all evaluation metrics and updates candidate's technical_test status.
    """
    try:
        service = TechnicalInterviewService(db)
        
        # Convert payload to dict
        completion_data = payload.model_dump(exclude_none=True)
        
        interview = await service.complete_interview(
            technical_interview_id,
            completion_data
        )
        
        if not interview:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Technical interview not found: {technical_interview_id}"
            )
        
        return ApiResponseSchema(
            success=True,
            message="Technical interview completed successfully",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_status": interview.interview_status,
                "overall_score": interview.overall_score,
                "overall_rating": interview.overall_rating,
                "result": interview.result,
                "ai_recommendation": interview.ai_recommendation,
                "ai_feedback_summary": interview.ai_feedback_summary,
                "candidate_strengths": interview.candidate_strengths,
                "candidate_weaknesses": interview.candidate_weaknesses,
                "improvement_areas": interview.improvement_areas,
                "interview_duration_seconds": interview.interview_duration_seconds
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete interview: {str(e)}"
        )


@router.get("/{technical_interview_id}", response_model=ApiResponseSchema[dict])
async def get_interview(
    technical_interview_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get complete technical interview data by ID.
    Returns all interview details including scores, transcript, and analysis.
    """
    try:
        service = TechnicalInterviewService(db)
        
        interview = await service.get_interview_by_id(technical_interview_id)
        
        if not interview:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Technical interview not found: {technical_interview_id}"
            )
        
        return ApiResponseSchema(
            success=True,
            message="Interview retrieved successfully",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "job_requirement_id": str(interview.job_requirement_id),
                "candidate_id": str(interview.candidate_id),
                "interview_session_id": interview.interview_session_id,
                "interview_started_at": interview.interview_started_at.isoformat() if interview.interview_started_at else None,
                "interview_ended_at": interview.interview_ended_at.isoformat() if interview.interview_ended_at else None,
                "interview_duration_seconds": interview.interview_duration_seconds,
                "interview_status": interview.interview_status,
                "overall_score": interview.overall_score,
                "overall_rating": interview.overall_rating,
                "technical_knowledge_score": interview.technical_knowledge_score,
                "domain_expertise_score": interview.domain_expertise_score,
                "communication_score": interview.communication_score,
                "language_proficiency_score": interview.language_proficiency_score,
                "confidence_score": interview.confidence_score,
                "professionalism_score": interview.professionalism_score,
                "response_relevance_score": interview.response_relevance_score,
                "response_depth_score": interview.response_depth_score,
                "response_clarity_score": interview.response_clarity_score,
                "total_questions_asked": interview.total_questions_asked,
                "questions_answered": interview.questions_answered,
                "questions_skipped": interview.questions_skipped,
                "average_response_time_seconds": interview.average_response_time_seconds,
                "longest_response_time_seconds": interview.longest_response_time_seconds,
                "shortest_response_time_seconds": interview.shortest_response_time_seconds,
                "total_speaking_time_seconds": interview.total_speaking_time_seconds,
                "engagement_score": interview.engagement_score,
                "follow_up_questions_asked": interview.follow_up_questions_asked,
                "interview_transcript": interview.interview_transcript,
                "question_analysis": interview.question_analysis,
                "skills_assessment": interview.skills_assessment,
                "candidate_strengths": interview.candidate_strengths,
                "candidate_weaknesses": interview.candidate_weaknesses,
                "ai_recommendation": interview.ai_recommendation,
                "ai_recommendation_reason": interview.ai_recommendation_reason,
                "ai_feedback_summary": interview.ai_feedback_summary,
                "improvement_areas": interview.improvement_areas,
                "interview_language": interview.interview_language,
                "languages_used": interview.languages_used,
                "ai_model_used": interview.ai_model_used,
                "video_enabled": interview.video_enabled,
                "input_tokens_used": interview.input_tokens_used,
                "output_tokens_used": interview.output_tokens_used,
                "audio_input_seconds": interview.audio_input_seconds,
                "audio_output_seconds": interview.audio_output_seconds,
                "result": interview.result,
                "passed_threshold": interview.passed_threshold,
                "created_at": interview.created_at.isoformat() if interview.created_at else None,
                "updated_at": interview.updated_at.isoformat() if interview.updated_at else None,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interview: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=ApiResponseSchema[dict])
async def get_interview_by_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get technical interview by session ID.
    Useful for the interview frontend to fetch interview context.
    """
    try:
        service = TechnicalInterviewService(db)
        
        interview = await service.get_interview_by_session(session_id)
        
        if not interview:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Interview session not found: {session_id}"
            )
        
        # Get job details
        job_repo = JobRequirementRepository(db)
        job = await job_repo.get_by_id(interview.job_requirement_id)
        
        # Get candidate details
        candidate_repo = CandidateRepository(db)
        candidate = await candidate_repo.get_by_id(interview.candidate_id)
        
        job_details = service._format_job_details(job)
        candidate_info = service._format_candidate_info(candidate)
        
        # Extract resume text for prompt
        resume_text = None
        if candidate and candidate.resume_url:
            resume_path = Path(candidate.resume_url)
            if resume_path.exists():
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(resume_path))
                    resume_text = ""
                    for page in reader.pages:
                        resume_text += page.extract_text() + "\n"
                except Exception:
                    pass
        
        system_instruction = service.generate_master_prompt(
            job_details=job_details,
            candidate_info=candidate_info,
            resume_text=resume_text
        )
        
        return ApiResponseSchema(
            success=True,
            message="Interview session retrieved",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "job_details": job_details,
                "candidate_info": candidate_info,
                "system_instruction": system_instruction,
                "interview_config": {
                    "min_duration_minutes": 5,
                    "max_duration_minutes": 15,
                    "auto_end_after_minutes": 15
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interview session: {str(e)}"
        )


@router.get("/job/{job_requirement_id}/interviews", response_model=ApiResponseSchema[dict])
async def get_interviews_by_job(
    job_requirement_id: UUID,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get all technical interviews for a job requirement.
    Optionally filter by status: pending, in_progress, completed, interrupted
    """
    try:
        service = TechnicalInterviewService(db)
        candidate_repo = CandidateRepository(db)

        interviews = await service.get_interviews_by_job(job_requirement_id, status)

        # Get all unique candidate IDs
        candidate_ids = list(set(interview.candidate_id for interview in interviews))

        # Fetch all candidates in one query for efficiency
        candidates_map = {}
        for cid in candidate_ids:
            candidate = await candidate_repo.get_by_id(cid)
            if candidate:
                candidates_map[str(cid)] = {
                    "name": f"{candidate.first_name} {candidate.last_name}",
                    "email": candidate.email
                }

        # Format interviews for response
        interviews_data = []
        for interview in interviews:
            candidate_info = candidates_map.get(str(interview.candidate_id), {})
            interviews_data.append({
                "technical_interview_id": str(interview.technical_interview_id),
                "candidate_id": str(interview.candidate_id),
                "candidate_name": candidate_info.get("name", "Unknown"),
                "candidate_email": candidate_info.get("email", ""),
                "session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "overall_score": interview.overall_score,
                "overall_rating": interview.overall_rating,
                "result": interview.result,
                "ai_recommendation": interview.ai_recommendation,
                "ai_feedback_summary": interview.ai_feedback_summary,
                "candidate_strengths": interview.candidate_strengths,
                "candidate_weaknesses": interview.candidate_weaknesses,
                "interview_duration_seconds": interview.interview_duration_seconds,
                "technical_knowledge_score": interview.technical_knowledge_score,
                "communication_score": interview.communication_score,
                "created_at": interview.created_at.isoformat() if interview.created_at else None
            })

        return ApiResponseSchema(
            success=True,
            message=f"Retrieved {len(interviews_data)} interviews",
            data={
                "job_requirement_id": str(job_requirement_id),
                "total_interviews": len(interviews_data),
                "status_filter": status,
                "interviews": interviews_data
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interviews: {str(e)}"
        )


@router.get("/job/{job_requirement_id}/statistics", response_model=ApiResponseSchema[dict])
async def get_interview_statistics(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get interview statistics for a job requirement.
    """
    try:
        service = TechnicalInterviewService(db)
        
        stats = await service.get_interview_statistics(job_requirement_id)
        
        return ApiResponseSchema(
            success=True,
            message="Interview statistics retrieved",
            data={
                "job_requirement_id": str(job_requirement_id),
                **stats
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/select-top-candidates", response_model=ApiResponseSchema[dict])
async def select_top_candidates(
    job_requirement_id: UUID,
    top_n: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Select top N candidates based on their technical interview scores.
    
    - Fetches all completed interviews for the given job requirement
    - Ranks candidates by overall score in descending order
    - Top N candidates get technical_test_result = 'pass'
    - Remaining candidates get technical_test_result = 'fail'
    
    **Parameters:**
    - job_requirement_id: UUID of the job requirement
    - top_n: Number of top candidates to select
    
    **Returns:**
    - List of selected (passed) candidates with their scores
    - List of rejected (failed) candidates with their scores
    """
    try:
        service = TechnicalInterviewService(db)
        
        result = await service.select_top_candidates(job_requirement_id, top_n)
        
        if result["total_interviews"] == 0:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="No completed technical interviews found for this job requirement"
            )
        
        return ApiResponseSchema(
            success=True,
            message=f"Successfully selected top {min(top_n, result['total_interviews'])} candidates out of {result['total_interviews']}",
            data={
                "job_requirement_id": str(job_requirement_id),
                "top_n_requested": top_n,
                **result
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select top candidates: {str(e)}"
        )


@router.get("/candidate/{candidate_id}/result", response_model=ApiResponseSchema[dict])
async def get_candidate_technical_result(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Return the candidate's latest technical interview with its numeric scores.

    Used by the candidate detail page to render the Technical gauge with a
    real percentage instead of just pass/fail. Returns data=null when the
    candidate has not completed a technical interview.
    """
    try:
        candidate_repo = CandidateRepository(db)
        interview_repo = TechnicalInterviewRepository(db)

        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}",
            )
        if not candidate.job_requirement_id:
            return ApiResponseSchema(success=True, message="No job linked", data=None)

        interview = await interview_repo.get_by_candidate_and_job(
            candidate_id, candidate.job_requirement_id
        )
        if not interview:
            return ApiResponseSchema(
                success=True,
                message="No technical interview yet for this candidate.",
                data=None,
            )

        return ApiResponseSchema(
            success=True,
            message="Technical interview retrieved",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "interview_started_at": interview.interview_started_at.isoformat() if interview.interview_started_at else None,
                "interview_ended_at": interview.interview_ended_at.isoformat() if interview.interview_ended_at else None,
                "interview_duration_seconds": interview.interview_duration_seconds,
                # Scores
                "overall_score": interview.overall_score,
                "overall_rating": interview.overall_rating,
                "technical_knowledge_score": interview.technical_knowledge_score,
                "domain_expertise_score": interview.domain_expertise_score,
                "communication_score": interview.communication_score,
                "language_proficiency_score": interview.language_proficiency_score,
                "confidence_score": interview.confidence_score,
                "professionalism_score": interview.professionalism_score,
                "response_relevance_score": interview.response_relevance_score,
                "response_depth_score": interview.response_depth_score,
                "response_clarity_score": interview.response_clarity_score,
                "engagement_score": getattr(interview, "engagement_score", None),
                "passed_threshold": getattr(interview, "passed_threshold", None),
                # Result + AI feedback
                "result": interview.result,
                "ai_recommendation": interview.ai_recommendation,
                "ai_recommendation_reason": interview.ai_recommendation_reason,
                "ai_feedback_summary": interview.ai_feedback_summary,
                "candidate_strengths": interview.candidate_strengths,
                "candidate_weaknesses": interview.candidate_weaknesses,
                "improvement_areas": interview.improvement_areas,
                # Rich data
                "interview_transcript": interview.interview_transcript,
                "skills_assessment": interview.skills_assessment,
                "question_analysis": interview.question_analysis,
                # Question stats
                "total_questions_asked": interview.total_questions_asked,
                "questions_answered": interview.questions_answered,
                "questions_skipped": interview.questions_skipped,
                # Metadata
                "interview_language": interview.interview_language,
                "languages_used": interview.languages_used,
                "candidate_technical_result": candidate.technical_test_result,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch technical interview: {str(e)}",
        )


@router.get("/candidate/{candidate_id}/status", response_model=ApiResponseSchema[dict])
async def get_candidate_interview_status(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Check if a candidate is eligible for technical interview.
    
    Returns:
    - Whether candidate has passed aptitude test
    - Whether technical interview is pending, completed, or not started
    - Interview URL if eligible
    """
    try:
        candidate_repo = CandidateRepository(db)
        interview_repo = TechnicalInterviewRepository(db)
        
        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}"
            )
        
        # Check aptitude test status
        aptitude_passed = candidate.aptitude_test and candidate.aptitude_test_result == "pass"
        
        # Check existing interview
        existing_interview = await interview_repo.get_pending_interview(
            candidate_id, candidate.job_requirement_id
        )
        
        completed_interview = await interview_repo.check_interview_exists(
            candidate_id, candidate.job_requirement_id
        )
        
        interview_status = "not_started"
        interview_url = None
        
        if completed_interview:
            interview_status = "completed"
        elif existing_interview:
            interview_status = existing_interview.interview_status
            interview_url = f"http://localhost:8100/interview/{existing_interview.interview_session_id}"
        
        return ApiResponseSchema(
            success=True,
            message="Candidate interview status retrieved",
            data={
                "candidate_id": str(candidate_id),
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "candidate_email": candidate.email,
                "job_requirement_id": str(candidate.job_requirement_id),
                "aptitude_test_passed": aptitude_passed,
                "eligible_for_technical_interview": aptitude_passed and not completed_interview,
                "interview_status": interview_status,
                "interview_url": interview_url,
                "technical_test_result": candidate.technical_test_result,
                "message": (
                    "Technical interview already completed" if completed_interview
                    else "Eligible for technical interview" if aptitude_passed
                    else "Must pass aptitude test first"
                )
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get candidate status: {str(e)}"
        )
