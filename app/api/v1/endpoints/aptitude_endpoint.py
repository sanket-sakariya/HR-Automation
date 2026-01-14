"""Aptitude Test Endpoints - Complete test management API."""

from __future__ import annotations
from typing import Optional
from uuid import UUID

import httpx
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
from app.repository.aptitude_test_repository import AptitudeTestRepository

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


@router.get("/generate-test-form/{job_requirement_id}/{aptitude_test_id}", response_model=ApiResponseSchema[dict])
async def generate_aptitude_test_form(
    job_requirement_id: UUID,
    aptitude_test_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Generate aptitude test form for a specific test.
    This endpoint fetches test details and questions from the database and generates the test form via the Flask service.
    """
    try:
        # Initialize services
        test_repo = AptitudeTestRepository(db)
        service = AptitudeTestService(db)

        # Verify the test exists and belongs to the job requirement
        test = await test_repo.get_test_by_id(aptitude_test_id)
        if not test:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Aptitude test not found: {aptitude_test_id}"
            )

        if test.job_requirement_id != job_requirement_id:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Test {aptitude_test_id} does not belong to job requirement {job_requirement_id}"
            )

        # Fetch all questions for the test
        questions = await test_repo.get_questions_by_test_id(aptitude_test_id)
        if not questions:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"No questions found for test {aptitude_test_id}"
            )

        # Prepare test details
        test_details = {
            "aptitude_test_id": str(test.aptitude_test_id),
            "job_requirement_id": str(test.job_requirement_id),
            "test_title": test.test_title,
            "total_questions": len(questions),
            "total_time_minutes": test.total_time_minutes,
            "passing_score_percentage": test.passing_score_percentage,
            "test_metadata": test.test_metadata,
            "proctoring_settings": test.proctoring_settings,
        }

        # Prepare questions data (without answers for security)
        questions_data = []
        for q in questions:
            questions_data.append({
                "question_id": str(q.question_id),
                "question_number": q.question_number,
                "difficulty": q.difficulty,
                "category": q.category,
                "question_text": q.question_text,
                "options": q.options,
                "time_allocated_seconds": q.time_allocated_seconds,
                "tags": q.tags
            })

        test_data = {
            "test_details": test_details,
            "questions": questions_data
        }

        # Print test details to terminal
        print("\n" + "="*80)
        print("🧠 APTITUDE TEST FORM GENERATION")
        print("="*80)
        print(f"🆔 Test ID: {test_details['aptitude_test_id']}")
        print(f"💼 Job Req ID: {test_details['job_requirement_id']}")
        print(f"📋 Test Title: {test_details['test_title']}")
        print(f"❓ Total Questions: {test_details['total_questions']}")
        print(f"⏱️  Total Time: {test_details['total_time_minutes']} minutes")
        print(f"📊 Passing Score: {test_details['passing_score_percentage']}%")
        print(f"🔒 Proctoring: {test_details.get('proctoring_settings', {}).get('tab_switch_detection', False)}")
        print("="*80 + "\n")

        # Call the Flask dynamic form service to generate the test form
        flask_service_url = f"http://localhost:8890/interview-management-service/api/v1/aptitude/generate-test-form/{job_requirement_id}/{aptitude_test_id}"

        async with httpx.AsyncClient() as client:
            # Send test data via POST to Flask service
            response = await client.post(
                flask_service_url,
                json={"test_data": test_data},
                timeout=30.0
            )

            if response.status_code == 200:
                flask_response = response.json()

                if flask_response.get("success"):
                    # Return test details and form URL
                    return ApiResponseSchema(
                        success=True,
                        message="Aptitude test form generated successfully",
                        data={
                            "test_details": test_details,
                            "questions_count": len(questions_data),
                            "form_url": flask_response.get("form_url"),
                            "form_path": flask_response.get("form_path"),
                            "test_access_url": f"{flask_response.get('form_url')}/start" if flask_response.get("form_url") else None
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to generate test form via Flask service: {flask_response.get('message')}"
                    )
            else:
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Flask service returned status {response.status_code}: {response.text}"
                )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to connect to Flask form service: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate aptitude test form: {str(e)}"
        )

