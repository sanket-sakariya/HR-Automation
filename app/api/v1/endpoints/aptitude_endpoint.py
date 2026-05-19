"""Aptitude Test Endpoints - Complete test management API."""

from __future__ import annotations
from typing import Optional
from uuid import UUID

import httpx
import secrets
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db
from app.config.constants import SuccessMessages

from app.schema.response_schema import ApiResponseSchema
from app.schema.aptitude_test_schema import (
    TestAnswerSubmit,
    TestAttemptResult,
    TestCreatedResponse
)

from app.service.aptitude_test_service import AptitudeTestService
from app.exception.job_requirement_exception import JobRequirementNotFoundException
from app.repository.aptitude_test_repository import AptitudeTestRepository
from app.repository.candidate_repository import CandidateRepository
from app.schema.candidate_management_schema import CandidateReadSchema

router = APIRouter(
    prefix="/aptitude",
    tags=["Aptitude Management"],
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


@router.get("/get-test-questions/{job_requirement_id}", response_model=ApiResponseSchema[dict])
async def get_test_questions(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aptitude test details and questions for a job requirement.

    This endpoint returns:
    - Test details (title, time limit, passing score, etc.)
    - All questions (without correct answers for security)

    Used by the frontend to display the test taking interface.
    """
    try:
        test_repo = AptitudeTestRepository(db)

        # Get the test by job requirement ID
        test = await test_repo.get_test_by_job_id(job_requirement_id)
        if not test:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"No aptitude test found for job requirement: {job_requirement_id}"
            )

        aptitude_test_id = test.aptitude_test_id

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

        # Sort questions by question_number
        questions_data.sort(key=lambda x: x["question_number"])

        return ApiResponseSchema(
            success=True,
            message="Test questions retrieved successfully",
            data={
                "test_details": test_details,
                "questions": questions_data
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test questions: {str(e)}"
        )


@router.get("/generate-test/{job_requirement_id}", response_model=ApiResponseSchema[dict])
async def generate_aptitude_test(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Generate aptitude test (both login form and test form) for a job requirement.

    This endpoint:
    1. Fetches test details and questions from the database
    2. Generates both login form and test form via the Flask service
    3. Returns URLs for both forms

    Candidates will first see the login form, and after successful login, they'll be redirected to the test form.
    """
    try:
        # Initialize services
        test_repo = AptitudeTestRepository(db)
        service = AptitudeTestService(db)

        # Get the test by job requirement ID
        test = await test_repo.get_test_by_job_id(job_requirement_id)
        if not test:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"No aptitude test found for job requirement: {job_requirement_id}"
            )

        aptitude_test_id = test.aptitude_test_id

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

        # Prepare combined data for Flask service
        combined_data = {
            "test_details": test_details,
            "questions": questions_data,
            "login_data": {
                "job_requirement_id": str(job_requirement_id),
                "aptitude_test_id": str(aptitude_test_id),
                "test_title": test.test_title,
                "login_instructions": "Please enter your email and password to access the aptitude test."
            }
        }

        # Print test details to terminal
        print("\n" + "="*80)
        print("🧠 APTITUDE TEST GENERATION (Login + Test Forms)")
        print("="*80)
        print(f"🆔 Test ID: {test_details['aptitude_test_id']}")
        print(f"💼 Job Req ID: {test_details['job_requirement_id']}")
        print(f"📋 Test Title: {test_details['test_title']}")
        print(f"❓ Total Questions: {test_details['total_questions']}")
        print(f"⏱️  Total Time: {test_details['total_time_minutes']} minutes")
        print(f"📊 Passing Score: {test_details['passing_score_percentage']}%")
        print(f"🔒 Proctoring: {test_details.get('proctoring_settings', {}).get('tab_switch_detection', False)}")
        print("="*80 + "\n")

        # Call the Flask service to generate both forms
        flask_service_url = f"http://localhost:8890/interview-management-service/api/v1/aptitude/generate-test/{job_requirement_id}"

        async with httpx.AsyncClient() as client:
            # Send combined data via POST to Flask service
            response = await client.post(
                flask_service_url,
                json=combined_data,
                timeout=30.0
            )

            if response.status_code == 200:
                flask_response = response.json()

                if flask_response.get("success"):              
                    # Return test details and both form URLs
                    return ApiResponseSchema(
                        success=True,
                        message="Aptitude test generated successfully (login + test forms)",
                        data={
                            "test_details": test_details,
                            "questions_count": len(questions_data),
                            "login_form_url": flask_response.get("login_form_url"),
                            "test_form_url": flask_response.get("test_form_url"),
                            "entry_url": flask_response.get("login_form_url"),  # Candidates start here
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to generate test via Flask service: {flask_response.get('message')}"
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
            detail=f"Failed to generate aptitude test: {str(e)}"
        )


@router.post("/validate-login/{job_requirement_id}/{aptitude_test_id}", response_model=ApiResponseSchema[dict])
async def validate_login(
    job_requirement_id: UUID,
    aptitude_test_id: UUID,
    login_data: dict,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Validate candidate login credentials and provide test access.
    Checks email and password against candidates table and manages test attempts.
    """
    try:
        # Extract login credentials
        email = login_data.get("email")
        password = login_data.get("password")

        if not email or not password:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )

        # Initialize repositories
        candidate_repo = CandidateRepository(db)
        test_repo = AptitudeTestRepository(db)

        # Verify the test exists
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

        # Find candidate by email and job_requirement_id
        # This ensures the candidate is specifically applying for this job
        candidate = await candidate_repo.get_by_email_and_job_requirement(email, job_requirement_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or candidate not found for this job requirement"
            )

        # Verify password
        if candidate.password != password:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if candidate already has an attempt for this test
        existing_attempt = await test_repo.get_attempt_by_email_and_test(email, aptitude_test_id)

        if existing_attempt:
            # If an attempt already exists and is completed (or any attempt number >=1), block further logins
            if (existing_attempt.user_attempt or 0) >= 1 and existing_attempt.status in {"completed", "in_progress", "pending"}:
                print(f"\n🚫 Attempt already used for {email}: Attempt #{existing_attempt.user_attempt} | Status: {existing_attempt.status}\n")
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Your chance has gone"
                )

            # Issue a fresh session token
            session_token = secrets.token_urlsafe(16)

            # If there is an existing record but not completed, allow resume
            attempt_data = {
                "attempt_id": str(existing_attempt.attempt_id),
                "status": existing_attempt.status,
                "user_attempt": existing_attempt.user_attempt,
                "message": "Existing attempt found"
            }

            # Direct test form URL (already generated by generate-test-form) - no token in URL
            test_form_url = f"http://localhost:8890/tests/{job_requirement_id}_{aptitude_test_id}.html"

            print(f"\n🔄 Existing attempt found for {email}: Attempt #{existing_attempt.user_attempt}")
            print(f"📊 Status: {existing_attempt.status}\n")

            # Return JSON so client JS can redirect cleanly
            return ApiResponseSchema(
                success=True,
                message="Login successful - existing attempt found",
                data={
                    "candidate_info": {
                        "candidate_id": str(candidate.candidate_id),
                        "email": candidate.email,
                        "first_name": candidate.first_name,
                        "last_name": candidate.last_name
                    },
                    "attempt_info": attempt_data,
                    "test_form_url": test_form_url,
                    "session_token": session_token,
                    "action": "existing_attempt"
                }
            )
        else:
            # First time attempt - create new attempt record
            attempt_data = {
                'aptitude_test_id': aptitude_test_id,
                'job_requirement_id': job_requirement_id,
                'candidate_email': email,
                'candidate_name': f"{candidate.first_name} {candidate.last_name}",
                'user_attempt': 1,  # First attempt
                'status': 'pending'
            }

            new_attempt = await test_repo.create_attempt(attempt_data)

            # Issue session token for the test session
            session_token = secrets.token_urlsafe(16)

            # Direct test form URL (token kept client-side only)
            test_form_url = f"http://localhost:8890/tests/{job_requirement_id}_{aptitude_test_id}.html"

            print(f"\n✅ New attempt created for {email}")
            print(f"🆔 Attempt ID: {new_attempt.attempt_id}")
            print(f"📊 Attempt #: {new_attempt.user_attempt}\n")

            # Return JSON so client JS can redirect cleanly
            return ApiResponseSchema(
                success=True,
                message="Login successful - new test attempt created",
                data={
                    "candidate_info": {
                        "candidate_id": str(candidate.candidate_id),
                        "email": candidate.email,
                        "first_name": candidate.first_name,
                        "last_name": candidate.last_name
                    },
                    "attempt_info": {
                        "attempt_id": str(new_attempt.attempt_id),
                        "status": new_attempt.status,
                        "user_attempt": new_attempt.user_attempt,
                        "message": "New test attempt created"
                    },
                    "test_form_url": test_form_url,
                    "session_token": session_token,
                    "action": "new_attempt"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login validation error: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login validation failed: {str(e)}"
        )


@router.post("/submit-test", response_model=ApiResponseSchema[TestAttemptResult])
async def submit_test(
    payload: TestAnswerSubmit,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Submit test answers and store results in aptitude_test_attempts.
    Calculates correct answers by matching with aptitude_questions.
    """
    try:
        service = AptitudeTestService(db)
        result = await service.submit_test_answers(
            attempt_id=payload.attempt_id,
            answers=payload.answers,
            time_taken_seconds=payload.time_taken_seconds,
            tab_switches=payload.tab_switches,
            keyboard_violations=payload.keyboard_violations
        )

        return ApiResponseSchema(
            success=True,
            message="Test submitted successfully",
            data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit test: {str(e)}"
        )


@router.get("/attempt/by-candidate/{candidate_id}", response_model=ApiResponseSchema[dict])
async def get_attempt_by_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Return the candidate's latest aptitude test attempt (score, correct count,
    passed flag, time taken, status). Used by the candidate detail page to
    display the aptitude score the same way it shows the resume score.

    Returns success=True with data={...} when an attempt exists,
    success=True with data=null when the candidate has no attempt yet.
    """
    try:
        candidate_repo = CandidateRepository(db)
        test_repo = AptitudeTestRepository(db)

        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}",
            )
        if not candidate.email or not candidate.job_requirement_id:
            return ApiResponseSchema(
                success=True,
                message="Candidate has no email or job — no attempt available.",
                data=None,
            )

        test = await test_repo.get_test_by_job_id(candidate.job_requirement_id)
        if not test:
            return ApiResponseSchema(
                success=True,
                message="No aptitude test exists for this candidate's job.",
                data=None,
            )

        attempt = await test_repo.get_attempt_by_email_and_test(
            candidate.email, test.aptitude_test_id
        )
        if not attempt:
            return ApiResponseSchema(
                success=True,
                message="No attempt yet for this candidate.",
                data=None,
            )

        return ApiResponseSchema(
            success=True,
            message="Attempt retrieved successfully",
            data={
                "attempt_id": str(attempt.attempt_id),
                "aptitude_test_id": str(attempt.aptitude_test_id),
                "job_requirement_id": str(attempt.job_requirement_id),
                "candidate_email": attempt.candidate_email,
                "candidate_name": attempt.candidate_name,
                "user_attempt": attempt.user_attempt,
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "time_taken_seconds": attempt.time_taken_seconds,
                "score": attempt.score,
                "correct_answers_count": attempt.correct_answers_count,
                "total_questions_attempted": attempt.total_questions_attempted,
                "passed": attempt.passed,
                "tab_switches": attempt.tab_switches,
                "status": attempt.status,
                "passing_score_percentage": test.passing_score_percentage,
                "total_questions": test.total_questions,
                "total_time_minutes": test.total_time_minutes,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch aptitude attempt: {str(e)}",
        )


@router.get("/answers/by-candidate/{candidate_id}", response_model=ApiResponseSchema[dict])
async def get_answers_by_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Return the candidate's aptitude attempt with full question/answer pairs.

    For each question in the test, includes:
      - question_text, options, category, difficulty
      - correct_answer (A/B/C/D)
      - candidate_answer (whatever they selected, or null)
      - is_correct (bool)

    Used by the detailed candidate report download.
    """
    try:
        candidate_repo = CandidateRepository(db)
        test_repo = AptitudeTestRepository(db)

        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}",
            )

        if not candidate.email or not candidate.job_requirement_id:
            return ApiResponseSchema(success=True, message="No attempt", data=None)

        test = await test_repo.get_test_by_job_id(candidate.job_requirement_id)
        if not test:
            return ApiResponseSchema(success=True, message="No test", data=None)

        attempt = await test_repo.get_attempt_by_email_and_test(
            candidate.email, test.aptitude_test_id
        )
        if not attempt:
            return ApiResponseSchema(success=True, message="No attempt", data=None)

        questions = await test_repo.get_questions_by_test_id(test.aptitude_test_id)
        candidate_answers = attempt.answers or {}

        qa: list = []
        for q in questions:
            # answers dict keys are stored as either question_number (int) or string;
            # try both shapes.
            ans_key_candidates = [
                str(q.question_number),
                str(q.question_number - 1),
                str(q.question_id),
            ]
            given = None
            for k in ans_key_candidates:
                if k in candidate_answers:
                    given = candidate_answers[k]
                    break
            qa.append({
                "question_number": q.question_number,
                "category": q.category,
                "difficulty": q.difficulty,
                "question_text": q.question_text,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "candidate_answer": given,
                "is_correct": (given is not None and str(given).upper() == str(q.correct_answer).upper()),
                "explanation": q.explanation,
            })

        return ApiResponseSchema(
            success=True,
            message="Q&A retrieved",
            data={
                "score": attempt.score,
                "correct_answers_count": attempt.correct_answers_count,
                "total_questions_attempted": attempt.total_questions_attempted,
                "passed": attempt.passed,
                "submitted_at": attempt.submitted_at,
                "questions": qa,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch aptitude answers: {str(e)}",
        )


@router.post("/reset-attempts/{candidate_id}", response_model=ApiResponseSchema[dict])
async def reset_candidate_aptitude_attempts(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset (delete) all aptitude test attempts for a candidate.

    HR uses this from the candidate detail page to allow a candidate
    to retake the aptitude test — clears the attempt rows so
    `user_attempt` effectively becomes 0 again, and clears the
    aptitude_test / aptitude_test_result flags on the candidate so
    the pipeline reopens for them.
    """
    try:
        candidate_repo = CandidateRepository(db)
        test_repo = AptitudeTestRepository(db)

        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Candidate not found: {candidate_id}"
            )
        if not candidate.email:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Candidate has no email — cannot reset attempts."
            )

        # Best-effort: scope to this candidate's job's test, if one exists
        aptitude_test_id = None
        try:
            test = await test_repo.get_test_by_job_id(candidate.job_requirement_id)
            if test:
                aptitude_test_id = test.aptitude_test_id
        except Exception:
            aptitude_test_id = None

        deleted = await test_repo.delete_attempts_by_email(
            email=candidate.email,
            aptitude_test_id=aptitude_test_id,
            job_requirement_id=candidate.job_requirement_id,
        )

        # Clear aptitude flags on the candidate so they can retake.
        try:
            candidate.aptitude_test = False
            candidate.aptitude_test_result = None
            await db.commit()
            await db.refresh(candidate)
        except Exception:
            await db.rollback()

        return ApiResponseSchema(
            success=True,
            message=(
                f"Reset complete — {deleted} previous attempt(s) cleared. "
                "Candidate can now log in and retake the aptitude test."
            ),
            data={
                "candidate_id": str(candidate_id),
                "email": candidate.email,
                "deleted_attempts": deleted,
                "aptitude_test_id": str(aptitude_test_id) if aptitude_test_id else None,
                "job_requirement_id": str(candidate.job_requirement_id),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset aptitude attempts: {str(e)}"
        )


@router.post("/select-top-candidates", response_model=ApiResponseSchema[dict])
async def select_top_candidates(
    job_requirement_id: UUID,
    aptitude_test_id: UUID,
    top_n: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Select top N candidates based on their aptitude test scores.
    
    - Fetches all completed attempts for the given job and aptitude test
    - Ranks candidates by score in descending order
    - Selects top N candidates as passed
    - Updates candidate table: aptitude_test=True for all, aptitude_test_result=True for passed, False for failed
    
    **Parameters:**
    - job_requirement_id: UUID of the job requirement
    - aptitude_test_id: UUID of the aptitude test
    - top_n: Number of top candidates to select (e.g., 5 means top 5 will pass)
    
    **Returns:**
    - List of selected (passed) candidates with their scores
    - List of rejected (failed) candidates with their scores
    """
    try:
        test_repo = AptitudeTestRepository(db)
        candidate_repo = CandidateRepository(db)
        
        # Verify the test exists
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
        
        # Get all completed attempts sorted by score (descending)
        attempts = await test_repo.get_completed_attempts_by_job_and_test(
            job_requirement_id=job_requirement_id,
            aptitude_test_id=aptitude_test_id
        )
        
        if not attempts:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="No completed test attempts found for this job and test"
            )
        
        total_attempts = len(attempts)
        
        # Determine which candidates passed (top N) and which failed (rest)
        passed_attempts = attempts[:top_n]
        failed_attempts = attempts[top_n:]
        
        # Prepare email lists for bulk update
        passed_emails = [attempt.candidate_email for attempt in passed_attempts]
        failed_emails = [attempt.candidate_email for attempt in failed_attempts]
        
        # Bulk update candidate records
        update_result = await candidate_repo.bulk_update_aptitude_test_results(
            job_requirement_id=job_requirement_id,
            passed_emails=passed_emails,
            failed_emails=failed_emails
        )
        
        # Prepare response data
        selected_candidates = [
            {
                "candidate_email": attempt.candidate_email,
                "candidate_name": attempt.candidate_name,
                "score": attempt.score,
                "rank": idx + 1,
                "status": "passed"
            }
            for idx, attempt in enumerate(passed_attempts)
        ]
        
        rejected_candidates = [
            {
                "candidate_email": attempt.candidate_email,
                "candidate_name": attempt.candidate_name,
                "score": attempt.score,
                "rank": top_n + idx + 1,
                "status": "failed"
            }
            for idx, attempt in enumerate(failed_attempts)
        ]
        
        return ApiResponseSchema(
            success=True,
            message=f"Successfully selected top {min(top_n, total_attempts)} candidates out of {total_attempts}",
            data={
                "job_requirement_id": str(job_requirement_id),
                "aptitude_test_id": str(aptitude_test_id),
                "total_attempts": total_attempts,
                "top_n_requested": top_n,
                "candidates_passed": len(selected_candidates),
                "candidates_failed": len(rejected_candidates),
                "selected_candidates": selected_candidates,
                "rejected_candidates": rejected_candidates,
                "update_summary": {
                    "candidates_updated_as_passed": len(update_result.get("updated_passed", [])),
                    "candidates_updated_as_failed": len(update_result.get("updated_failed", [])),
                    "candidates_not_found": update_result.get("not_found", [])
                }
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select top candidates: {str(e)}"
        )

