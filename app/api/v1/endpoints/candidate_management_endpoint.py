from __future__ import annotations

import asyncio
import httpx
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status as http_status, UploadFile, File, Form
from fastapi.responses import HTMLResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db

from app.config.constants import SuccessMessages, ApiErrorMessages

from app.helper.fastapi.get_header import get_list_params, get_user_id, get_workspace_id

from app.schema.response_schema import (
    ApiResponseSchema,
    PaginatedResponseSchema,
    PaginationMeta,
    ListParamsSchema,
)

from app.schema.candidate_management_schema import (
    CandidateCreateSchema,
    CandidateReadSchema,
    CandidateUpdateSchema,
    CandidateListParamsSchema,
    JobApplicationFormSchema,
)

from app.service.candidate_management_service import CandidateManagementService

from app.exception.candidate_management_exception import (
    CandidateNotFoundException,
    CandidateCreationException,
    CandidateUpdateException,
    CandidateDeletionException,
    DuplicateApplicationException,
)

from app.exception.job_requirement_exception import JobRequirementNotFoundException
from app.exception.baseapp_exception import InternalServerErrorException

router = APIRouter(
    prefix="/candidates",
    tags=["Candidate Management"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)



@router.get("/apply/{job_requirement_id}", response_model=ApiResponseSchema[dict])
async def get_application_form(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get job requirement details and generate application form for a specific job requirement.
    This endpoint fetches job details from the database and generates the form via the Flask service.
    """
    try:
        # First, fetch job requirement details from database
        service = CandidateManagementService(db)
        
        from app.repository.job_requirement_repository import JobRequirementRepository
        job_repo = JobRequirementRepository(db=db)
        
        # Fetch job requirement (without workspace_id since this is a public form)
        job_requirement = await job_repo.get_by_id(job_requirement_id)
        
        if not job_requirement:
            raise JobRequirementNotFoundException(job_requirement_id)
        
        # Prepare job details
        job_details = {
            "job_requirement_id": str(job_requirement.job_requirement_id),
            "title": job_requirement.title,
            "department": job_requirement.department,
            "description": job_requirement.description,
            "requirements": job_requirement.requirements,
            "location": job_requirement.location,
            "job_type": job_requirement.job_type,
            "salary_range": job_requirement.salary_range,
            "benefits": job_requirement.benefits if hasattr(job_requirement, 'benefits') else None,
            "experience": job_requirement.experience if hasattr(job_requirement, 'experience') else None,
            "company_id": str(job_requirement.company_id) if hasattr(job_requirement, 'company_id') else None,
        }
        
        # Print job details to terminal
        print("\n" + "="*80)
        print("📋 JOB REQUIREMENT DETAILS - APPLICATION FORM")
        print("="*80)
        print(f"🆔 Job ID: {job_details['job_requirement_id']}")
        print(f"📌 Title: {job_details['title']}")
        print(f"🏢 Department: {job_details['department']}")
        print(f"📍 Location: {job_details['location']}")
        print(f"💼 Job Type: {job_details['job_type']}")
        print(f"📝 Description: {job_details['description'][:100]}..." if len(job_details['description']) > 100 else f"📝 Description: {job_details['description']}")
        if job_details.get('salary_range'):
            print(f"💰 Salary Range: {job_details['salary_range']}")
        if job_details.get('experience'):
            print(f"🎓 Experience Required: {job_details['experience']}")
        if job_details.get('requirements'):
            print(f"✅ Requirements: {job_details['requirements']}")
        print("="*80 + "\n")

        # Call the Flask dynamic form service to generate the form with job details
        flask_service_url = f"http://localhost:8889/interview-management-service/api/v1/candidates/apply/{job_requirement_id}"

        async with httpx.AsyncClient() as client:
            # Send job details via POST to Flask service
            response = await client.post(
                flask_service_url,
                json={"job_details": job_details},
                timeout=10.0
            )

            if response.status_code == 200:
                flask_response = response.json()

                if flask_response.get("success"):
                    # Return both job details and form URL
                    return ApiResponseSchema(
                        success=True,
                        message="Job details retrieved and form generated successfully",
                        data={
                            "job_details": job_details,
                            "form_url": flask_response.get("form_url"),
                            "form_path": flask_response.get("form_path")
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to generate form via Flask service: {flask_response.get('message')}"
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
    except JobRequirementNotFoundException as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Job requirement not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate application form: {str(e)}"
        )


@router.post("/apply", response_model=ApiResponseSchema[CandidateReadSchema])
async def submit_application(
    job_requirement_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    portfolio_url: Optional[str] = Form(None),
    current_location: Optional[str] = Form(None),
    willing_to_relocate: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    expected_salary: Optional[str] = Form(None),
    notice_period: Optional[str] = Form(None),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Submit job application with form data and resume upload.
    Handles file upload, stores candidate information, and analyzes resume using AI.
    """
    try:
        service = CandidateManagementService(db)

        # Convert form data to proper types
        candidate_data = {
            "job_requirement_id": job_requirement_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "linkedin_url": linkedin_url,
            "portfolio_url": portfolio_url,
            "current_location": current_location,
            "willing_to_relocate": willing_to_relocate.lower() == "true" if willing_to_relocate else False,
            "expected_salary": float(expected_salary) if expected_salary else None,
            "notice_period": notice_period,
        }

        # Parse skills if provided
        if skills:
            candidate_data["skills"] = [skill.strip() for skill in skills.split(",") if skill.strip()]

        # Validate data
        candidate_schema = CandidateCreateSchema(**candidate_data)

        # Create candidate (this will generate candidate_id internally)
        candidate = await service.create_candidate_application(
            job_requirement_id=UUID(job_requirement_id),
            payload=candidate_schema,
        )

        # Save resume file
        resume_path = await service.save_resume_file(
            file=resume,
            candidate_id=candidate.candidate_id,
            job_requirement_id=UUID(job_requirement_id)
        )

        # Prepare candidate data for AI analysis
        analysis_candidate_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'skills': candidate_data.get('skills'),  # Already parsed as list
            'expected_salary': candidate_data.get('expected_salary'),
            'notice_period': notice_period,
            'current_location': current_location,
            'willing_to_relocate': candidate_data.get('willing_to_relocate'),
            'linkedin_url': linkedin_url,
            'portfolio_url': portfolio_url,
        }

        # Analyze resume using AI with both resume content and form data
        resume_score = await service.analyze_and_score_resume(
            candidate_id=candidate.candidate_id,
            job_requirement_id=UUID(job_requirement_id),
            resume_path=resume_path,
            candidate_data=analysis_candidate_data
        )

        # Update candidate with resume path and AI-generated score
        update_data = {"resume_url": resume_path}
        if resume_score is not None:
            update_data["candidate_resume_score"] = resume_score
        
        # Log the update data for debugging
        from app.config.logger_config import log_central
        log_central(
            f"Updating candidate with data: {update_data} [candidate_id={candidate.candidate_id}]",
            level="info"
        )

        updated_candidate = await service.update_candidate(
            candidate_id=candidate.candidate_id,
            payload=CandidateUpdateSchema(**update_data),
        )
        
        log_central(
            f"Candidate updated - resume_score in object: {updated_candidate.candidate_resume_score} [candidate_id={candidate.candidate_id}]",
            level="info"
        )

        # Refresh candidate to get updated data from database
        final_candidate = await service.get_candidate_by_id(candidate.candidate_id)
        
        log_central(
            f"Final candidate from DB - resume_score: {final_candidate.candidate_resume_score} [candidate_id={candidate.candidate_id}]",
            level="info"
        )

        return ApiResponseSchema(
            success=True,
            message=SuccessMessages.CANDIDATE_APPLICATION_CREATED,
            data=final_candidate
        )

    except DuplicateApplicationException as e:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="You have already applied to this job position."
        )
    except JobRequirementNotFoundException as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Job requirement not found: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data provided: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit application: {str(e)}"
        )


@router.get("/{candidate_id}", response_model=ApiResponseSchema[CandidateReadSchema])
async def get_candidate(
    candidate_id: UUID,
    workspace_id: Optional[str] = None,  # Accept but ignore workspace-id header
    db: AsyncSession = Depends(get_async_db),
):
    """Get candidate details by ID."""
    try:
        service = CandidateManagementService(db)

        candidate = await service.get_candidate_by_id(candidate_id)

        return ApiResponseSchema(
            success=True,
            message=SuccessMessages.CANDIDATE_RETRIEVED,
            data=candidate
        )

    except CandidateNotFoundException as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve candidate: {str(e)}"
        )


@router.get("/", response_model=ApiResponseSchema[PaginatedResponseSchema[CandidateReadSchema]])
async def list_candidates(
    job_requirement_id: UUID,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """List candidates filtered by job_requirement_id with pagination and optional filters."""
    try:
        service = CandidateManagementService(db)

        # Create params with job_requirement_id filter
        params = CandidateListParamsSchema(
            page=page,
            limit=limit,
            job_requirement_id=job_requirement_id,
            status=status,
            search=search
        )

        result = await service.get_candidates(params)

        # Convert to paginated response format
        offset = (params.page - 1) * params.limit
        pagination_meta = PaginationMeta(
            total_count=result.get("total", 0),
            offset=offset,
            limit=params.limit,
            total_pages=result.get("total_pages", 0)
        )

        paginated_response = PaginatedResponseSchema(
            success=True,
            message=SuccessMessages.CANDIDATES_RETRIEVED,
            data=result.get("data", []),
            pagination=pagination_meta
        )

        return ApiResponseSchema(
            success=True,
            message=SuccessMessages.CANDIDATES_RETRIEVED,
            data=paginated_response
        )

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve candidates: {str(e)}"
        )


@router.post("/select-top-resumes/{job_requirement_id}", response_model=ApiResponseSchema[dict])
async def select_top_resumes(
    job_requirement_id: UUID,
    top_n: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Select top N candidates based on their resume scores for a job requirement.
    
    - Fetches all candidates for the given job requirement with resume scores
    - Ranks candidates by resume score in descending order
    - Sets resume_selected=True for top N candidates
    - Sets resume_selected=False for remaining candidates
    
    **Parameters:**
    - job_requirement_id: UUID of the job requirement
    - top_n: Number of top candidates to select (e.g., 5 means top 5 will be selected)
    
    **Returns:**
    - List of selected candidates with their resume scores
    - List of rejected candidates with their resume scores
    """
    try:
        from app.repository.candidate_repository import CandidateRepository
        
        candidate_repo = CandidateRepository(db)
        
        # Bulk update resume_selected for candidates
        result = await candidate_repo.bulk_update_resume_selected(
            job_requirement_id=job_requirement_id,
            top_n=top_n
        )
        
        if result["total_candidates"] == 0:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="No candidates with resume scores found for this job requirement"
            )
        
        return ApiResponseSchema(
            success=True,
            message=f"Successfully selected top {min(top_n, result['total_candidates'])} resumes out of {result['total_candidates']} candidates",
            data={
                "job_requirement_id": str(job_requirement_id),
                "top_n_requested": top_n,
                "total_candidates": result["total_candidates"],
                "selected_count": result["selected_count"],
                "rejected_count": result["rejected_count"],
                "selected_candidates": result["selected_candidates"],
                "rejected_candidates": result["rejected_candidates"]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select top resumes: {str(e)}"
        )




@router.post("/{candidate_id}/comprehensive-report", response_model=ApiResponseSchema[dict])
async def generate_comprehensive_report(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Generate an AI-driven holistic hiring report for a candidate.

    Pulls together:
      - Candidate profile + resume score
      - Aptitude Q&A (questions + given answers + correct answers)
      - Technical interview transcript + per-skill scores + AI feedback
      - HR interview transcript + per-skill scores + AI feedback

    Sends everything to Gemini to produce a structured narrative:
      hire_recommendation, executive_summary, technical_assessment,
      behavioral_assessment, communication_assessment, cultural_fit_assessment,
      key_strengths, key_concerns, risk_areas, next_steps
    """
    import json as _json
    try:
        # ---- Load everything we need
        from app.repository.candidate_repository import CandidateRepository
        from app.repository.aptitude_test_repository import AptitudeTestRepository
        from app.repository.technical_interview_repository import TechnicalInterviewRepository
        from app.repository.hr_interview_repository import HRInterviewRepository

        candidate_repo = CandidateRepository(db)
        candidate = await candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Aptitude Q&A
        aptitude_qa: list = []
        aptitude_summary = None
        try:
            apt_repo = AptitudeTestRepository(db)
            test = (
                await apt_repo.get_test_by_job_id(candidate.job_requirement_id)
                if candidate.job_requirement_id else None
            )
            if test and candidate.email:
                attempt = await apt_repo.get_attempt_by_email_and_test(
                    candidate.email, test.aptitude_test_id
                )
                if attempt:
                    aptitude_summary = {
                        "score": attempt.score,
                        "correct": attempt.correct_answers_count,
                        "total": attempt.total_questions_attempted,
                        "passed": attempt.passed,
                    }
                    questions = await apt_repo.get_questions_by_test_id(test.aptitude_test_id)
                    answers = attempt.answers or {}
                    for q in questions:
                        given = None
                        for k in (str(q.question_number), str(q.question_number - 1), str(q.question_id)):
                            if k in answers:
                                given = answers[k]
                                break
                        aptitude_qa.append({
                            "q_no": q.question_number,
                            "category": q.category,
                            "question": q.question_text,
                            "given": given,
                            "correct": q.correct_answer,
                            "is_correct": (
                                given is not None
                                and str(given).upper() == str(q.correct_answer).upper()
                            ),
                        })
        except Exception as _e:
            pass

        # Technical interview
        tech_data = None
        try:
            tech_repo = TechnicalInterviewRepository(db)
            tech = (
                await tech_repo.get_by_candidate_and_job(candidate_id, candidate.job_requirement_id)
                if candidate.job_requirement_id else None
            )
            if tech:
                tech_data = {
                    "overall_score": tech.overall_score,
                    "result": tech.result,
                    "duration_seconds": tech.interview_duration_seconds,
                    "scores": {
                        "technical_knowledge": tech.technical_knowledge_score,
                        "domain_expertise": tech.domain_expertise_score,
                        "communication": tech.communication_score,
                        "confidence": tech.confidence_score,
                        "professionalism": tech.professionalism_score,
                        "response_relevance": tech.response_relevance_score,
                        "response_depth": tech.response_depth_score,
                        "response_clarity": tech.response_clarity_score,
                    },
                    "ai_feedback": tech.ai_feedback_summary,
                    "ai_recommendation": tech.ai_recommendation,
                    "strengths": tech.candidate_strengths,
                    "weaknesses": tech.candidate_weaknesses,
                    "transcript": tech.interview_transcript,
                }
        except Exception as _e:
            pass

        # HR interview
        hr_data = None
        try:
            hr_repo = HRInterviewRepository(db)
            hr = (
                await hr_repo.get_by_candidate_and_job(candidate_id, candidate.job_requirement_id)
                if candidate.job_requirement_id else None
            )
            if hr:
                hr_data = {
                    "overall_score": hr.overall_score,
                    "result": hr.result,
                    "duration_seconds": hr.interview_duration_seconds,
                    "scores": {
                        "communication": hr.communication_score,
                        "articulation": getattr(hr, "articulation_score", None),
                        "confidence": hr.confidence_score,
                        "professionalism": hr.professionalism_score,
                        "attitude": getattr(hr, "attitude_score", None),
                        "teamwork": getattr(hr, "teamwork_score", None),
                        "leadership": getattr(hr, "leadership_score", None),
                        "problem_solving": getattr(hr, "problem_solving_score", None),
                        "adaptability": getattr(hr, "adaptability_score", None),
                        "cultural_fit": getattr(hr, "cultural_fit_score", None),
                        "motivation": getattr(hr, "motivation_score", None),
                    },
                    "ai_feedback": hr.ai_feedback_summary,
                    "ai_recommendation": hr.ai_recommendation,
                    "strengths": hr.candidate_strengths,
                    "weaknesses": hr.candidate_weaknesses,
                    "transcript": hr.interview_transcript,
                }
        except Exception as _e:
            pass

        # Resume score
        resume_score = getattr(candidate, "candidate_resume_score", None)

        # ---- Build Gemini prompt
        full_name = f"{candidate.first_name or ''} {candidate.last_name or ''}".strip()
        prompt = f"""You are a senior hiring manager writing the final comprehensive evaluation report for a candidate.

Use ONLY the data below. Be specific, cite concrete examples from the transcripts and aptitude answers. Do NOT invent facts.

# Candidate
- Name: {full_name}
- Email: {candidate.email}
- Resume AI Match Score: {resume_score if resume_score is not None else 'N/A'}/100

# Aptitude Test
{_json.dumps(aptitude_summary, indent=2) if aptitude_summary else 'Not taken'}

Per-question performance (sample):
{_json.dumps(aptitude_qa[:20], indent=2, default=str) if aptitude_qa else 'N/A'}

# Technical Interview
{_json.dumps(tech_data, indent=2, default=str)[:6000] if tech_data else 'Not taken'}

# HR Interview
{_json.dumps(hr_data, indent=2, default=str)[:6000] if hr_data else 'Not taken'}

# Output
Return ONLY valid JSON with this exact schema:
{{
  "hire_recommendation": "strong_hire | hire | neutral | no_hire | strong_no_hire",
  "confidence": "high | medium | low",
  "headline": "<one-line verdict>",
  "executive_summary": "<3-5 sentences synthesizing the entire pipeline performance>",
  "technical_assessment": "<2-3 paragraphs evaluating technical depth, knowledge breadth, problem-solving — cite specific transcript quotes or aptitude answers>",
  "behavioral_assessment": "<2-3 paragraphs on behavioral patterns: STAR usage, examples given, self-awareness, handling of difficult questions — cite specific HR transcript moments>",
  "communication_assessment": "<2 paragraphs on language clarity, articulation, listening, language switches if any>",
  "cultural_fit_assessment": "<2 paragraphs on attitude, motivation, team fit, values alignment>",
  "key_strengths": ["<concrete strength 1>", "<2>", "<3>", "<4>"],
  "key_concerns": ["<concrete concern 1>", "<2>", "<3>"],
  "risk_areas": ["<onboarding risk>", "<performance risk>", "<retention risk>"],
  "recommended_next_steps": ["<action 1>", "<action 2>", "<action 3>"],
  "comparison_vs_role": "<2 sentences on how candidate stacks up against the role's typical bar>",
  "overall_score_out_of_10": <number>
}}
"""

        # ---- Call Gemini
        try:
            import google.generativeai as genai
            genai.configure(api_key="AIzaSyDHNd6W382fBzwf_HbPxf70sxG13XE9xgA")
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            text = response.text or "{}"
            ai_report = _json.loads(text)
        except Exception as gem_err:
            ai_report = {
                "hire_recommendation": "neutral",
                "confidence": "low",
                "headline": "AI report generation failed — see raw scores",
                "executive_summary": f"Automated narrative could not be produced ({gem_err}). Refer to per-section scores and raw transcripts.",
            }

        return ApiResponseSchema(
            success=True,
            message="Report generated",
            data={
                "candidate_name": full_name,
                "candidate_email": candidate.email,
                "job_requirement_id": str(candidate.job_requirement_id) if candidate.job_requirement_id else None,
                "resume_score": resume_score,
                "aptitude": {
                    "summary": aptitude_summary,
                    "qa": aptitude_qa,
                },
                "technical": tech_data,
                "hr": hr_data,
                "ai_report": ai_report,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )
