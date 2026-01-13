"""Aptitude Test Endpoints - Complete test management API."""

from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db
from app.config.constants import SuccessMessages

from app.schema.response_schema import ApiResponseSchema
from app.schema.aptitude_test_schema import (
    TestAttemptStart,
    TestAttemptVerifyOTP,
    TestAnswerSubmit,
    OTPSentResponse,
    TestAccessResponse,
    TestAttemptResult,
    TestCreatedResponse
)

from app.service.aptitude_test_service import AptitudeTestService
from app.exception.job_requirement_exception import JobRequirementNotFoundException

router = APIRouter(
    prefix="/aptitude",
    tags=["Aptitude Tests"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


@router.post("/create/{job_requirement_id}", response_model=ApiResponseSchema[dict])
async def create_aptitude_test(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new aptitude test for a job requirement.
    
    - Generates 30 AI-powered questions
    - Stores questions and answers in database
    - Returns test ID and public URL
    
    **Note:** If test already exists for this job, returns existing test.
    """
    try:
        service = AptitudeTestService(db)
        
        # Generate and store test
        result = await service.generate_and_store_test(job_requirement_id)
        
        # Generate public URL
        public_url = f"http://localhost:8888/interview-management-service/api/v1/aptitude/test/{job_requirement_id}/{result['aptitude_test_id']}"
        
        return ApiResponseSchema(
            success=True,
            message="Aptitude test created successfully" if not result.get('already_exists') else "Test already exists",
            data={
                "aptitude_test_id": str(result['aptitude_test_id']),
                "job_requirement_id": str(job_requirement_id),
                "test_title": result.get('test_title', 'Aptitude Test'),
                "total_questions": 30,
                "questions_generated": result.get('questions_generated', 30),
                "already_exists": result.get('already_exists', False),
                "public_url": public_url,
                "test_access_url": f"{public_url}/start"
            }
        )

    except JobRequirementNotFoundException as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Job requirement not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create aptitude test: {str(e)}"
        )


@router.get("/test/{job_requirement_id}/{aptitude_test_id}")
async def get_test_info(
    job_requirement_id: UUID,
    aptitude_test_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get test information (landing page).
    
    Returns test details without questions.
    Users need to enter email and verify OTP to access the actual test.
    """
    try:
        from app.repository.aptitude_test_repository import AptitudeTestRepository
        
        repo = AptitudeTestRepository(db)
        test = await repo.get_test_by_id(aptitude_test_id)
        
        if not test or test.job_requirement_id != job_requirement_id:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Test not found"
            )
        
        return ApiResponseSchema(
            success=True,
            message="Test information retrieved",
            data={
                "test_title": test.test_title,
                "total_questions": test.total_questions,
                "total_time_minutes": test.total_time_minutes,
                "passing_score_percentage": test.passing_score_percentage,
                "instructions": [
                    "Enter your email address to receive OTP",
                    "Verify OTP to start the test",
                    f"You have {test.total_time_minutes} minutes to complete {test.total_questions} questions",
                    f"You need {test.passing_score_percentage}% to pass",
                    "Tab switching is monitored (max 3 switches allowed)",
                    "Copy-paste is disabled during the test"
                ]
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test info: {str(e)}"
        )


@router.post("/test/{job_requirement_id}/{aptitude_test_id}/start", response_model=ApiResponseSchema[OTPSentResponse])
async def start_test(
    job_requirement_id: UUID,
    aptitude_test_id: UUID,
    payload: TestAttemptStart,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Start a test attempt - sends OTP to candidate's email.
    
    - Creates a test attempt record
    - Generates 6-digit OTP
    - Sends OTP to candidate's email
    - Returns attempt_id for OTP verification
    """
    try:
        service = AptitudeTestService(db)
        
        result = await service.start_test_attempt(
            job_requirement_id=job_requirement_id,
            aptitude_test_id=aptitude_test_id,
            candidate_email=payload.candidate_email,
            candidate_name=payload.candidate_name
        )
        
        return ApiResponseSchema(
            success=True,
            message=result['message'],
            data={
                "attempt_id": str(result['attempt_id']),
                "message": result['message'],
                "email": payload.candidate_email,
                "expires_in_minutes": 10
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start test: {str(e)}"
        )


@router.post("/verify-otp", response_model=ApiResponseSchema[dict])
async def verify_otp(
    payload: TestAttemptVerifyOTP,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Verify OTP and get test questions.
    
    - Verifies the OTP code
    - Marks attempt as verified and in-progress
    - Returns all test questions (without correct answers)
    - Starts the test timer
    """
    try:
        service = AptitudeTestService(db)
        
        result = await service.verify_otp_and_get_test(
            attempt_id=payload.attempt_id,
            otp_code=payload.otp_code
        )
        
        return ApiResponseSchema(
            success=True,
            message="OTP verified successfully. Test started!",
            data={
                "test": result['test'],
                "attempt_id": result['attempt_id'],
                "candidate_name": result.get('candidate_name'),
                "time_remaining_seconds": result['test']['total_time_minutes'] * 60
            }
        )

    except Exception as e:
        if "Invalid OTP" in str(e):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code. Please try again."
            )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify OTP: {str(e)}"
        )


@router.post("/submit", response_model=ApiResponseSchema[TestAttemptResult])
async def submit_test(
    payload: TestAnswerSubmit,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Submit test answers and get results.
    
    - Validates answers against correct answers in database
    - Calculates score and pass/fail status
    - Records proctoring violations (tab switches)
    - Returns detailed results
    """
    try:
        service = AptitudeTestService(db)
        
        result = await service.submit_test_answers(
            attempt_id=payload.attempt_id,
            answers=payload.answers,
            time_taken_seconds=payload.time_taken_seconds,
            tab_switches=payload.tab_switches
        )
        
        return ApiResponseSchema(
            success=True,
            message=f"Test submitted successfully! Score: {result['score']}%",
            data=result
        )

    except Exception as e:
        if "already submitted" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Test has already been submitted"
            )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit test: {str(e)}"
        )


@router.get("/results/{attempt_id}", response_model=ApiResponseSchema[dict])
async def get_test_results(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get test results for a specific attempt.
    
    Returns detailed results including score, answers, and proctoring data.
    """
    try:
        from app.repository.aptitude_test_repository import AptitudeTestRepository
        
        repo = AptitudeTestRepository(db)
        attempt = await repo.get_attempt_by_id(attempt_id)
        
        if not attempt:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Test attempt not found"
            )
        
        if attempt.status != 'completed':
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Test not yet completed"
            )
        
        return ApiResponseSchema(
            success=True,
            message="Results retrieved successfully",
            data={
                "attempt_id": str(attempt.attempt_id),
                "candidate_email": attempt.candidate_email,
                "candidate_name": attempt.candidate_name,
                "score": attempt.score,
                "correct_answers_count": attempt.correct_answers_count,
                "total_questions_attempted": attempt.total_questions_attempted,
                "passed": attempt.passed,
                "time_taken_seconds": attempt.time_taken_seconds,
                "tab_switches": attempt.tab_switches,
                "submitted_at": attempt.submitted_at
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get results: {str(e)}"
        )

