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
    Generate application form for a specific job requirement and return the URL to access it.
    This endpoint generates the form via the Flask service and returns JSON with the form URL.
    """
    try:
        # Call the Flask dynamic form service to generate the form
        import httpx

        flask_service_url = f"http://localhost:8889/interview-management-service/api/v1/candidates/apply/{job_requirement_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(flask_service_url)

            if response.status_code == 200:
                flask_response = response.json()

                if flask_response.get("success"):
                    # Return the form URL from Flask service
                    return ApiResponseSchema(
                        success=True,
                        message="Form generated successfully",
                        data={
                            "job_requirement_id": str(job_requirement_id),
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
    Handles file upload and stores candidate information.
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

        # Update candidate with resume path
        await service.update_candidate(
            candidate_id=candidate.candidate_id,
            payload=CandidateUpdateSchema(resume_url=resume_path),
        )

        return ApiResponseSchema(
            success=True,
            message=SuccessMessages.CANDIDATE_APPLICATION_CREATED,
            data=candidate
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
