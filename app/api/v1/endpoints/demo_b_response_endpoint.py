from __future__ import annotations

from uuid import UUID

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

from app.schema.demo_b_response_schema import (
    DemoBResponseCreateSchema,
    DemoBResponseUpdateSchema,
    DemoBResponseReadSchema,
    DemoBResponseStatusUpdateSchema,
    DemoBResponseIsActiveUpdateSchema,
)

from app.service.demo_b_response_service import DemoBResponseService

from app.exception.demo_b_response_exception import (
    DemoBResponseNotFoundException,
    DemoBResponseCreationException,
    DemoBResponseUpdateException,
    DemoBResponseDeletionException,
    DemoBResponseInvalidDataException,
    DemoBResponsePermissionDeniedException,
)

from app.exception.baseapp_exception import InternalServerErrorException

router = APIRouter(route_class=RedisCachedRoute)


# Create a new DemoBResponse
@router.post(
    "/demo-b-response/create/",
    response_model=ApiResponseSchema[DemoBResponseReadSchema],
    status_code=http_status.HTTP_201_CREATED,
)
async def create_demo_b_response(
    payload: DemoBResponseCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Create a new demo B response.

    This endpoint allows creating a demo B response.
    """
    try:
        # Create demo B response using the schema
        data = await DemoBResponseService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoBResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_RESPONSE_CREATED
        )

    except (
        DemoBResponseCreationException,
        DemoBResponseInvalidDataException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve a DemoBResponse by ID
@router.get(
    "/demo-b-response/read/{demo_b_response_id}/", response_model=ApiResponseSchema[DemoBResponseReadSchema]
)
async def get_demo_b_response(
    demo_b_response_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a demo B response by ID."""

    try:
        data = await DemoBResponseService(db).read(
            demo_b_response_id=demo_b_response_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoBResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_RESPONSE_RETRIEVED
        )
    except (
        DemoBResponseNotFoundException,
        DemoBResponsePermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Get all DemoBResponses by demo_b_id
@router.get(
    "/demo-b-response/by-demo-b/{demo_b_id}/", response_model=ApiResponseSchema[list[DemoBResponseReadSchema]]
)
async def get_demo_b_responses_by_demo_b_id(
    demo_b_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve all demo B responses for a specific demo_b_id."""

    try:
        data = await DemoBResponseService(db).get_by_demo_b_id(
            demo_b_id=demo_b_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[list[DemoBResponseReadSchema]](
            success=True, data=data, message=SuccessMessages.DEMO_B_RESPONSES_RETRIEVED
        )
    except (
        DemoBResponsePermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all DemoBResponses
@router.get("/demo-b-responses/", response_model=PaginatedResponseSchema[list[DemoBResponseReadSchema]])
async def list_demo_b_responses(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all demo B responses."""
    try:
        # Use filters directly (already parsed in get_list_params)
        result = await DemoBResponseService(db).list_all(
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

        return PaginatedResponseSchema[list[DemoBResponseReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.DEMO_B_RESPONSES_RETRIEVED,
        )
    except (DemoBResponsePermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update a DemoBResponse
@router.patch(
    "/demo-b-response/update/{demo_b_response_id}/", response_model=ApiResponseSchema[DemoBResponseReadSchema]
)
async def update_demo_b_response(
    demo_b_response_id: UUID,
    payload: DemoBResponseUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing demo B response.

    This endpoint allows updating demo B response fields.
    """
    try:
        # Update demo B response using the schema
        data = await DemoBResponseService(db).update(
            demo_b_response_id=demo_b_response_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return ApiResponseSchema[DemoBResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_RESPONSE_UPDATED
        )

    except (
        DemoBResponseNotFoundException,
        DemoBResponseUpdateException,
        DemoBResponseInvalidDataException,
        DemoBResponsePermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_UPDATE_FAILED}: {str(e)}",
        ) from e


# Update is_active of a DemoBResponse
@router.patch(
    "/demo-b-response/update/is-active/{demo_b_response_id}/",
    response_model=ApiResponseSchema[DemoBResponseReadSchema],
)
async def update_demo_b_response_is_active(
    demo_b_response_id: UUID,
    payload: DemoBResponseIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo B response is_active status.

    Updates only the is_active field of the demo B response.
    """
    try:
        data = await DemoBResponseService(db).update_is_active(
            demo_b_response_id=demo_b_response_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return ApiResponseSchema[DemoBResponseReadSchema](
            success=True,
            data=data,
            message=SuccessMessages.DEMO_B_RESPONSE_ACTIVE_STATUS_UPDATED,
        )
    except (
        DemoBResponseNotFoundException,
        DemoBResponseUpdateException,
        DemoBResponsePermissionDeniedException,
        DemoBResponseInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e

# Update DemoBResponse status
@router.patch(
    "/demo-b-response/update/status/{demo_b_response_id}/",
    response_model=ApiResponseSchema[DemoBResponseReadSchema],
)
async def update_demo_b_response_status(
    demo_b_response_id: UUID,
    payload: DemoBResponseStatusUpdateSchema,  # Use the correct schema
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo B response status and error messages.

    Updates the demo B response status, error_message, and error_user_message fields.
    """
    try:
        data = await DemoBResponseService(db).update_status(
            demo_b_response_id=demo_b_response_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return ApiResponseSchema[DemoBResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_RESPONSE_STATUS_UPDATED
        )
    except (
        DemoBResponseNotFoundException,
        DemoBResponseUpdateException,
        DemoBResponsePermissionDeniedException,
        DemoBResponseInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e

# Delete a DemoBResponse
@router.delete("/demo-b-response/delete/{demo_b_response_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo_b_response(
    demo_b_response_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete a demo B response by ID."""
    try:
        await DemoBResponseService(db).delete(
            demo_b_response_id=demo_b_response_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_B_RESPONSE_DELETED
        )
    except (
        DemoBResponseNotFoundException,
        DemoBResponseDeletionException,
        DemoBResponsePermissionDeniedException,
        DemoBResponseInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RESPONSE_DELETION_FAILED}: {str(e)}",
        ) from e

