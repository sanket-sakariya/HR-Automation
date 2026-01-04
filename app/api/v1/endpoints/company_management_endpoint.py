from __future__ import annotations

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

from app.schema.company_management_schema import (
    CompanyCreateSchema,
    CompanyUpdateSchema,
    CompanyReadSchema,
    CompanyListParamsSchema,
)

from app.service.company_management_service import CompanyManagementService

from app.exception.company_management_exception import (
    CompanyNotFoundException,
    CompanyAlreadyExistsException,
    CompanyCreationException,
    CompanyUpdateException,
    CompanyDeletionException,
    CompanyInvalidDataException,
    CompanyPermissionDeniedException,
)

from app.exception.baseapp_exception import InternalServerErrorException

router = APIRouter(route_class=RedisCachedRoute)


# ==================== COMPANY ENDPOINTS ====================

# Create a new Company
@router.post(
    "/companies/register/",
    response_model=ApiResponseSchema[CompanyReadSchema],
    status_code=http_status.HTTP_201_CREATED,
)
async def create_company(
    payload: CompanyCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Register a new company.

    This endpoint allows registering a new company on the platform.
    """
    try:
        data = await CompanyManagementService(db).create_company(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[CompanyReadSchema](
            success=True, data=data, message=SuccessMessages.COMPANY_CREATED
        )

    except (
        CompanyCreationException,
        CompanyInvalidDataException,
        CompanyAlreadyExistsException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.COMPANY_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve a Company by ID
@router.get(
    "/companies/{company_id}/",
    response_model=ApiResponseSchema[CompanyReadSchema]
)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a company by ID."""

    try:
        data = await CompanyManagementService(db).get_company(
            company_id=company_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[CompanyReadSchema](
            success=True, data=data, message=SuccessMessages.COMPANY_RETRIEVED
        )
    except (
        CompanyNotFoundException,
        CompanyPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.COMPANY_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all Companies
@router.get(
    "/companies/",
    response_model=PaginatedResponseSchema[list[CompanyReadSchema]]
)
async def list_companies(
    params: CompanyListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all companies."""

    try:
        result = await CompanyManagementService(db).list_companies(
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

        return PaginatedResponseSchema[list[CompanyReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.COMPANIES_RETRIEVED,
        )
    except (CompanyPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.COMPANIES_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update a Company
@router.put(
    "/companies/{company_id}/",
    response_model=ApiResponseSchema[CompanyReadSchema]
)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing company.

    This endpoint allows updating company profile and settings.
    """
    try:
        data = await CompanyManagementService(db).update_company(
            company_id=company_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return ApiResponseSchema[CompanyReadSchema](
            success=True, data=data, message=SuccessMessages.COMPANY_UPDATED
        )

    except (
        CompanyNotFoundException,
        CompanyUpdateException,
        CompanyInvalidDataException,
        CompanyPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.COMPANY_UPDATE_FAILED}: {str(e)}",
        ) from e


# Delete a Company
@router.delete(
    "/companies/{company_id}/",
    response_model=ApiResponseSchema[dict]
)
async def delete_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Delete a company.

    This endpoint performs a soft delete of the company.
    """
    try:
        await CompanyManagementService(db).delete_company(
            company_id=company_id, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.COMPANY_DELETED
        )

    except (
        CompanyNotFoundException,
        CompanyDeletionException,
        CompanyPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.COMPANY_DELETION_FAILED}: {str(e)}",
        ) from e


