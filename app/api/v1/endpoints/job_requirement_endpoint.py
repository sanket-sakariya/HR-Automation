from __future__ import annotations

import asyncio
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db

from app.config.constants import SuccessMessages, ApiErrorMessages

from app.helper.fastapi.get_header import get_list_params, get_user_id, get_workspace_id

from app.helper.redis_cached_route_helper import RedisCachedRoute

from app.schema.response_schema import (
    ApiResponseSchema,
    PaginatedResponseSchema,
    PaginationMeta,
    ListParamsSchema,
)

from app.schema.job_requirement_schema import (
    JobRequirementCreateSchema,
    JobRequirementUpdateSchema,
    JobRequirementReadSchema,
    JobRequirementListParamsSchema,
    JobRequirementStatusUpdateSchema,
    JobRequirementStatus,
)

from app.service.job_requirement_service import JobRequirementService

from app.exception.job_requirement_exception import (
    JobRequirementNotFoundException,
    JobRequirementCreationException,
    JobRequirementUpdateException,
    JobRequirementDeletionException,
    JobRequirementInvalidDataException,
    JobRequirementPermissionDeniedException,
)

from app.exception.company_management_exception import CompanyNotFoundException
from app.exception.baseapp_exception import InternalServerErrorException

from app.service.linkedin_service import LinkedInService


router = APIRouter(route_class=RedisCachedRoute)


# Create a new Job Requirement
@router.post(
    "/companies/{company_id}/job-requirements/",
    response_model=ApiResponseSchema[JobRequirementReadSchema],
    status_code=http_status.HTTP_201_CREATED,
)
async def create_job_requirement(
    company_id: UUID,
    payload: JobRequirementCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Create a new job requirement for a company.

    This endpoint creates a new job requirement for the specified company.
    """
    try:
        # Create job requirement and get LinkedIn posting data from service
        data, linkedin_job_data = await JobRequirementService(db).create_job_requirement_with_linkedin_data(
            company_id=company_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id
        )

        # Start LinkedIn posting in background
        linkedin_service = LinkedInService()

        async def post_to_linkedin_background():
            """Background task for LinkedIn posting with error handling"""
            try:
                await linkedin_service.post_job_to_linkedin(linkedin_job_data)
            except Exception as e:
                print(f"❌ LinkedIn posting failed for job {data.job_requirement_id}: {str(e)}")
                # Log the error but don't fail the API response
                import logging
                logging.error(f"LinkedIn posting failed for job {data.job_requirement_id}: {str(e)}")

        asyncio.create_task(post_to_linkedin_background())

        # Update response message to indicate LinkedIn posting is initiated
        enhanced_message = f"{SuccessMessages.JOB_REQUIREMENT_CREATED} LinkedIn posting initiated."

        return ApiResponseSchema[JobRequirementReadSchema](
            success=True, data=data, message=enhanced_message
        )

    except (
        JobRequirementCreationException,
        JobRequirementInvalidDataException,
        CompanyNotFoundException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENT_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve a Job Requirement by ID
@router.get(
    "/job-requirements/{job_requirement_id}/",
    response_model=ApiResponseSchema[JobRequirementReadSchema]
)
async def get_job_requirement(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a job requirement by ID."""

    try:
        data = await JobRequirementService(db).get_job_requirement(
            job_requirement_id=job_requirement_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[JobRequirementReadSchema](
            success=True, data=data, message=SuccessMessages.JOB_REQUIREMENT_RETRIEVED
        )
    except (
        JobRequirementNotFoundException,
        JobRequirementPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENT_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all Job Requirements
@router.get(
    "/job-requirements/",
    response_model=PaginatedResponseSchema[list[JobRequirementReadSchema]]
)
async def list_job_requirements(
    status: Optional[JobRequirementStatus] = None,
    params: JobRequirementListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all job requirements with optional filters."""

    try:
        result = await JobRequirementService(db).list_job_requirements(
            status=status,
            filters=params.filters,
            search=params.search,
            order_by=params.order_by,
            skip=params.offset,
            limit=params.limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        # Extract data and pagination info from service result
        data = result.get("data", [])
        pagination_data = result.get("pagination", {})

        # Use pagination data from service, with fallback calculations
        total_count = pagination_data.get("total_count", len(data))
        total_pages = pagination_data.get(
            "total_pages",
            (total_count + params.limit - 1) // params.limit if total_count > 0 else 0,
        )

        pagination = PaginationMeta(
            total_count=total_count,
            offset=params.offset,
            limit=params.limit,
            total_pages=total_pages,
        )

        return PaginatedResponseSchema[list[JobRequirementReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.JOB_REQUIREMENTS_RETRIEVED,
        )
    except (JobRequirementPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENTS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List Job Requirements for a specific Company
@router.get(
    "/companies/{company_id}/job-requirements/",
    response_model=PaginatedResponseSchema[list[JobRequirementReadSchema]]
)
async def list_job_requirements_by_company(
    company_id: UUID,
    status: Optional[JobRequirementStatus] = None,
    params: JobRequirementListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List job requirements for a specific company."""

    try:
        result = await JobRequirementService(db).list_job_requirements_by_company(
            company_id=company_id,
            status=status,
            filters=params.filters,
            search=params.search,
            order_by=params.order_by,
            skip=params.offset,
            limit=params.limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        # Extract data and pagination info from service result
        data = result.get("data", [])
        pagination_data = result.get("pagination", {})

        pagination = PaginationMeta(
            total_count=pagination_data.get("total_count", len(data)),
            offset=params.offset,
            limit=params.limit,
            total_pages=pagination_data.get("total_pages", 1),
        )

        return PaginatedResponseSchema[list[JobRequirementReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.JOB_REQUIREMENTS_RETRIEVED,
        )
    except (
        CompanyNotFoundException,
        JobRequirementPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENTS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update a Job Requirement
@router.put(
    "/job-requirements/{job_requirement_id}/",
    response_model=ApiResponseSchema[JobRequirementReadSchema]
)
async def update_job_requirement(
    job_requirement_id: UUID,
    payload: JobRequirementUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing job requirement.

    This endpoint allows updating job requirement details.
    """
    try:
        data = await JobRequirementService(db).update_job_requirement(
            job_requirement_id=job_requirement_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return ApiResponseSchema[JobRequirementReadSchema](
            success=True, data=data, message=SuccessMessages.JOB_REQUIREMENT_UPDATED
        )

    except (
        JobRequirementNotFoundException,
        JobRequirementUpdateException,
        JobRequirementInvalidDataException,
        JobRequirementPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENT_UPDATE_FAILED}: {str(e)}",
        ) from e


# Update Job Requirement Status
@router.patch(
    "/job-requirements/{job_requirement_id}/status/",
    response_model=ApiResponseSchema[JobRequirementReadSchema]
)
async def update_job_requirement_status(
    job_requirement_id: UUID,
    payload: JobRequirementStatusUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update the status of a job requirement.

    This endpoint allows updating only the status of a job requirement.
    """
    try:
        data = await JobRequirementService(db).update_job_requirement_status(
            job_requirement_id=job_requirement_id,
            status=payload.status,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return ApiResponseSchema[JobRequirementReadSchema](
            success=True, data=data, message="Job requirement status updated successfully"
        )

    except (
        JobRequirementNotFoundException,
        JobRequirementUpdateException,
        JobRequirementPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENT_UPDATE_FAILED}: {str(e)}",
        ) from e


# Delete a Job Requirement
@router.delete(
    "/job-requirements/{job_requirement_id}/",
    response_model=ApiResponseSchema[dict]
)
async def delete_job_requirement(
    job_requirement_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Delete a job requirement.

    This endpoint performs a soft delete of the job requirement.
    """
    try:
        await JobRequirementService(db).delete_job_requirement(
            job_requirement_id=job_requirement_id, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.JOB_REQUIREMENT_DELETED
        )

    except (
        JobRequirementNotFoundException,
        JobRequirementDeletionException,
        JobRequirementPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.JOB_REQUIREMENT_DELETION_FAILED}: {str(e)}",
        ) from e
