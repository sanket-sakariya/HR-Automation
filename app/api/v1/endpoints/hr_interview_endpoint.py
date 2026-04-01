"""HR Interview Endpoints - Complete HR interview management API."""

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
from app.schema.hr_interview_schema import (
    HRInterviewStartRequest,
    CompleteHRInterviewRequest,
)

from app.service.hr_interview_service import HRInterviewService
from app.repository.hr_interview_repository import HRInterviewRepository
from app.repository.candidate_repository import CandidateRepository
from app.repository.job_requirement_repository import JobRequirementRepository

# HR interview service URL
HR_INTERVIEW_SERVICE_URL = "http://localhost:8200"

router = APIRouter(
    prefix="/hr-interview",
    tags=["HR Interview Management"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


@router.post("/start/{candidate_id}", response_model=ApiResponseSchema[dict])
async def start_hr_interview(
    candidate_id: UUID,
    payload: HRInterviewStartRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Start HR Interview for a Candidate.
    
    Flow:
    1. Verify candidate exists and job requirement matches
    2. Check if candidate passed technical interview
    3. Get candidate details including resume
    4. Generate master AI prompt for HR interview
    5. Create interview session
    6. Return interview URL and details
    
    Interview Duration: Minimum 5 minutes, Maximum 12 minutes
    
    Request Body:
    - job_requirement_id: UUID of the job requirement
    
    No email/password required - interview starts directly.
    """
    try:
        service = HRInterviewService(db)
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
        
        # Step 3: Check if candidate passed technical interview
        if not candidate.technical_test or candidate.technical_test_result != "pass":
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Candidate must pass technical interview before HR interview"
            )
        
        # Step 4: Check if candidate has already taken HR interview
        if candidate.hr_test and candidate.hr_test_result:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Candidate has already completed HR interview with result: {candidate.hr_test_result}"
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
        
        # Step 8: Generate master AI prompt for HR interview
        system_instruction = service.generate_master_prompt(
            job_details=job_details,
            candidate_info=candidate_info,
            resume_text=resume_text
        )
        
        # WebSocket URL for the interview (pointing to the hr-interview-service on port 8200)
        websocket_url = f"ws://localhost:8200/ws/interview/{interview.interview_session_id}"
        interview_url = f"http://localhost:8200/interview/{interview.interview_session_id}"
        
        # Step 9: Register the session with the hr-interview-service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                register_response = await client.post(
                    f"{HR_INTERVIEW_SERVICE_URL}/register-session",
                    json={
                        "session_id": interview.interview_session_id,
                        "job_details": job_details,
                        "candidate_info": candidate_info,
                        "system_instruction": system_instruction,
                        "hr_interview_id": str(interview.hr_interview_id)
                    }
                )
                if register_response.status_code != 200:
                    print(f"Warning: Could not register session with hr-interview-service: {register_response.text}")
        except Exception as e:
            print(f"Warning: Could not connect to hr-interview-service: {e}")
            # Continue anyway - the session might need to be registered manually
        
        return ApiResponseSchema(
            success=True,
            message="HR interview started successfully. Interview duration: 5-12 minutes.",
            data={
                "hr_interview_id": str(interview.hr_interview_id),
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
                    "max_duration_minutes": 12,
                    "auto_end_after_minutes": 12
                },
                "instructions": {
                    "1": "Open the interview_url in your browser",
                    "2": "Allow microphone and camera permissions",
                    "3": "Click 'Start Interview' to begin",
                    "4": "Speak clearly - the AI supports English, Hindi, and Gujarati",
                    "5": "Interview will last between 5-12 minutes"
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start HR interview: {str(e)}"
        )


@router.post("/complete/{hr_interview_id}", response_model=ApiResponseSchema[dict])
async def complete_interview(
    hr_interview_id: UUID,
    payload: CompleteHRInterviewRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Complete the HR interview with all scores and analysis.
    This endpoint is called by the AI interview system after the interview ends.
    
    Stores all evaluation metrics and updates candidate's hr_interview status.
    """
    try:
        service = HRInterviewService(db)
        
        # Convert payload to dict
        completion_data = payload.model_dump(exclude_none=True)
        
        interview = await service.complete_interview(
            hr_interview_id,
            completion_data
        )
        
        if not interview:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"HR interview not found: {hr_interview_id}"
            )
        
        return ApiResponseSchema(
            success=True,
            message="HR interview completed successfully",
            data={
                "hr_interview_id": str(interview.hr_interview_id),
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


@router.get("/{hr_interview_id}", response_model=ApiResponseSchema[dict])
async def get_interview(
    hr_interview_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get complete HR interview data by ID.
    Returns all interview details including scores, transcript, and analysis.
    """
    try:
        service = HRInterviewService(db)
        
        interview = await service.get_interview_by_id(hr_interview_id)
        
        if not interview:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"HR interview not found: {hr_interview_id}"
            )
        
        return ApiResponseSchema(
            success=True,
            message="Interview retrieved successfully",
            data={
                "hr_interview_id": str(interview.hr_interview_id),
                "job_requirement_id": str(interview.job_requirement_id),
                "candidate_id": str(interview.candidate_id),
                "interview_session_id": interview.interview_session_id,
                "interview_started_at": interview.interview_started_at.isoformat() if interview.interview_started_at else None,
                "interview_ended_at": interview.interview_ended_at.isoformat() if interview.interview_ended_at else None,
                "interview_duration_seconds": interview.interview_duration_seconds,
                "interview_status": interview.interview_status,
                "overall_score": interview.overall_score,
                "overall_rating": interview.overall_rating,
                "communication_score": interview.communication_score,
                "language_proficiency_score": interview.language_proficiency_score,
                "articulation_score": interview.articulation_score,
                "confidence_score": interview.confidence_score,
                "professionalism_score": interview.professionalism_score,
                "attitude_score": interview.attitude_score,
                "teamwork_score": interview.teamwork_score,
                "leadership_score": interview.leadership_score,
                "problem_solving_score": interview.problem_solving_score,
                "adaptability_score": interview.adaptability_score,
                "cultural_fit_score": interview.cultural_fit_score,
                "motivation_score": interview.motivation_score,
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
                "soft_skills_assessment": interview.soft_skills_assessment,
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
    Get HR interview by session ID.
    Useful for the interview frontend to fetch interview context.
    """
    try:
        service = HRInterviewService(db)
        
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
                "hr_interview_id": str(interview.hr_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "job_details": job_details,
                "candidate_info": candidate_info,
                "system_instruction": system_instruction,
                "interview_config": {
                    "min_duration_minutes": 5,
                    "max_duration_minutes": 12,
                    "auto_end_after_minutes": 12
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
    Get all HR interviews for a job requirement.
    Optionally filter by status: pending, in_progress, completed, interrupted
    """
    try:
        service = HRInterviewService(db)
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
                "hr_interview_id": str(interview.hr_interview_id),
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
                "communication_score": interview.communication_score,
                "cultural_fit_score": interview.cultural_fit_score,
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
        service = HRInterviewService(db)
        
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
    Select top N candidates based on their HR interview scores.
    
    - Fetches all completed interviews for the given job requirement
    - Ranks candidates by overall score in descending order
    - Top N candidates get hr_interview_result = 'pass'
    - Remaining candidates get hr_interview_result = 'fail'
    
    **Parameters:**
    - job_requirement_id: UUID of the job requirement
    - top_n: Number of top candidates to select
    
    **Returns:**
    - List of selected (passed) candidates with their scores
    - List of rejected (failed) candidates with their scores
    """
    try:
        service = HRInterviewService(db)
        
        result = await service.select_top_candidates(job_requirement_id, top_n)
        
        if result["total_interviews"] == 0:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="No completed HR interviews found for this job requirement"
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


@router.get("/candidate/{candidate_id}/status", response_model=ApiResponseSchema[dict])
async def get_candidate_interview_status(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Check if a candidate is eligible for HR interview.
    
    Returns:
    - Whether candidate has passed technical interview
    - Whether HR interview is pending, completed, or not started
    - Interview URL if eligible
    """
    try:
        candidate_repo = CandidateRepository(db)
        interview_repo = HRInterviewRepository(db)
        
        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}"
            )
        
        # Check technical interview status
        technical_passed = candidate.technical_test and candidate.technical_test_result == "pass"
        
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
            interview_url = f"http://localhost:8200/interview/{existing_interview.interview_session_id}"
        
        return ApiResponseSchema(
            success=True,
            message="Candidate interview status retrieved",
            data={
                "candidate_id": str(candidate_id),
                "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                "candidate_email": candidate.email,
                "job_requirement_id": str(candidate.job_requirement_id),
                "technical_interview_passed": technical_passed,
                "eligible_for_hr_interview": technical_passed and not completed_interview,
                "interview_status": interview_status,
                "interview_url": interview_url,
                "hr_test_result": candidate.hr_test_result,
                "message": (
                    "HR interview already completed" if completed_interview
                    else "Eligible for HR interview" if technical_passed
                    else "Must pass technical interview first"
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
