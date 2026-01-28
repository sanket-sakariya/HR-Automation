"""Technical Interview Endpoints - Complete interview management API."""

from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db
from app.config.constants import SuccessMessages

from app.schema.response_schema import ApiResponseSchema
from app.schema.technical_interview_schema import (
    TechnicalInterviewLoginRequest,
    StartTechnicalInterviewRequest,
    CompleteInterviewRequest,
    TechnicalInterviewReadSchema,
    TechnicalInterviewDetailedSchema,
    InterviewSessionResponse,
)

from app.service.technical_interview_service import TechnicalInterviewService
from app.repository.technical_interview_repository import TechnicalInterviewRepository
from app.repository.candidate_repository import CandidateRepository
from app.repository.job_requirement_repository import JobRequirementRepository

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
async def candidate_login(
    payload: TechnicalInterviewLoginRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Candidate login for technical interview.
    Uses the same credentials as aptitude test (email + auto-generated password).
    
    Returns interview session details and WebSocket URL for the AI interview.
    """
    try:
        service = TechnicalInterviewService(db)
        
        # Validate credentials
        validation = await service.validate_candidate_login(
            email=payload.email,
            password=payload.password,
            job_requirement_id=payload.job_requirement_id
        )
        
        if not validation.get("valid"):
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail=validation.get("error", "Invalid credentials")
            )
        
        candidate = validation["candidate"]
        
        # Create interview session
        session_result = await service.create_interview_session(
            candidate_id=candidate.candidate_id,
            job_requirement_id=payload.job_requirement_id
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
        
        # Generate customized system instruction
        system_instruction = service.generate_system_instruction(job_details)
        
        # WebSocket URL for the interview (pointing to the technical-interview-service on port 8100)
        websocket_url = f"ws://localhost:8100/ws/{interview.interview_session_id}"
        
        return ApiResponseSchema(
            success=True,
            message="Login successful. Ready to start technical interview.",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "is_existing_session": session_result.get("is_existing", False),
                "websocket_url": websocket_url,
                "interview_url": f"http://localhost:8100/interview/{interview.interview_session_id}",
                "job_details": job_details,
                "candidate_info": candidate_info,
                "system_instruction": system_instruction,
                "instructions": {
                    "1": "Open the interview_url in your browser",
                    "2": "Allow microphone and camera permissions",
                    "3": "Click 'Start Interview' to begin",
                    "4": "Speak clearly in English, Hindi, or Gujarati",
                    "5": "The AI will adapt to your language preference"
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/start/{technical_interview_id}", response_model=ApiResponseSchema[dict])
async def start_interview(
    technical_interview_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Mark the technical interview as started.
    Call this when the candidate begins the actual interview.
    """
    try:
        service = TechnicalInterviewService(db)
        
        interview = await service.start_interview(technical_interview_id)
        
        if not interview:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Technical interview not found: {technical_interview_id}"
            )
        
        return ApiResponseSchema(
            success=True,
            message="Technical interview started",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "started_at": interview.interview_started_at.isoformat() if interview.interview_started_at else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview: {str(e)}"
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


@router.get("/{technical_interview_id}", response_model=ApiResponseSchema[TechnicalInterviewReadSchema])
async def get_interview(
    technical_interview_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get technical interview details by ID.
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
            data=interview
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interview: {str(e)}"
        )


@router.get("/detailed/{technical_interview_id}", response_model=ApiResponseSchema[TechnicalInterviewDetailedSchema])
async def get_interview_detailed(
    technical_interview_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get detailed technical interview data including transcript and analysis.
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
            message="Detailed interview data retrieved successfully",
            data=interview
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interview details: {str(e)}"
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
        system_instruction = service.generate_system_instruction(job_details)
        
        return ApiResponseSchema(
            success=True,
            message="Interview session retrieved",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_status": interview.interview_status,
                "job_details": job_details,
                "candidate_info": {
                    "candidate_id": str(candidate.candidate_id) if candidate else None,
                    "name": f"{candidate.first_name} {candidate.last_name}" if candidate else None,
                    "email": candidate.email if candidate else None
                },
                "system_instruction": system_instruction
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
        
        interviews = await service.get_interviews_by_job(job_requirement_id, status)
        
        # Format interviews for response
        interviews_data = []
        for interview in interviews:
            interviews_data.append({
                "technical_interview_id": str(interview.technical_interview_id),
                "candidate_id": str(interview.candidate_id),
                "interview_status": interview.interview_status,
                "overall_score": interview.overall_score,
                "overall_rating": interview.overall_rating,
                "result": interview.result,
                "ai_recommendation": interview.ai_recommendation,
                "interview_duration_seconds": interview.interview_duration_seconds,
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


@router.post("/generate-test-url", response_model=ApiResponseSchema[dict])
async def generate_technical_test_url(
    job_requirement_id: UUID,
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Generate a technical test URL for a candidate.
    
    This endpoint creates a new interview session and returns the URL
    that the candidate can use to access the interview portal.
    
    **Parameters:**
    - job_requirement_id: UUID of the job requirement
    - candidate_id: UUID of the candidate
    
    **Returns:**
    - Interview URL pointing to technical interview service on port 8100
    - Interview session details
    """
    try:
        service = TechnicalInterviewService(db)
        
        # Create interview session
        session_result = await service.create_interview_session(
            candidate_id=candidate_id,
            job_requirement_id=job_requirement_id
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
        
        # Generate URLs
        interview_url = f"http://localhost:8100/interview/{interview.interview_session_id}"
        login_url = f"http://localhost:8100/?job={job_requirement_id}"
        
        return ApiResponseSchema(
            success=True,
            message="Technical interview URL generated successfully",
            data={
                "technical_interview_id": str(interview.technical_interview_id),
                "interview_session_id": interview.interview_session_id,
                "interview_url": interview_url,
                "login_url": login_url,
                "direct_access_url": f"http://localhost:8100/interview/{interview.interview_session_id}",
                "job_details": {
                    "job_id": str(job_requirement_id),
                    "title": job_details.get("title", ""),
                    "department": job_details.get("department", "")
                },
                "candidate_info": {
                    "candidate_id": str(candidate_id),
                    "name": candidate_info.get("name", ""),
                    "email": candidate_info.get("email", "")
                },
                "is_existing_session": session_result.get("is_existing", False),
                "instructions": {
                    "step_1": "Share the interview_url with the candidate",
                    "step_2": "Candidate logs in with their email and password",
                    "step_3": "Allow microphone and camera permissions",
                    "step_4": "Complete the AI-powered voice interview"
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test URL: {str(e)}"
        )
