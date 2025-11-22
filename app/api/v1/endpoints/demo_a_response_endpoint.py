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

from app.schema.demo_a_response_schema import (
    DemoAResponseCreateSchema,
    DemoAResponseUpdateSchema,
    DemoAResponseReadSchema,
    DemoAResponseStatusUpdateSchema,
    DemoAResponseIsActiveUpdateSchema,
)

from app.service.demo_a_response_service import DemoAResponseService

from app.exception.demo_a_response_exception import (
    DemoAResponseNotFoundException,
    DemoAResponseCreationException,
    DemoAResponseUpdateException,
    DemoAResponseDeletionException,
    DemoAResponseInvalidDataException,
    DemoAResponsePermissionDeniedException,
)

from app.exception.baseapp_exception import InternalServerErrorException

router = APIRouter(route_class=RedisCachedRoute)


# Create a new DemoAResponse
@router.post(
    "/demo-a-response/create/",
    response_model=ApiResponseSchema[DemoAResponseReadSchema],
    status_code=http_status.HTTP_201_CREATED,
)
async def create_demo_a_response(
    payload: DemoAResponseCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Create a new demo A response.

    This endpoint allows creating a demo A response.
    """
    try:
        # Create demo A response using the schema
        data = await DemoAResponseService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_RESPONSE_CREATED
        )

    except (
        DemoAResponseCreationException,
        DemoAResponseInvalidDataException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve a DemoAResponse by ID
@router.get(
    "/demo-a-response/read/{demo_a_response_id}/", response_model=ApiResponseSchema[DemoAResponseReadSchema]
)
async def get_demo_a_response(
    demo_a_response_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a demo A response by ID."""

    try:
        data = await DemoAResponseService(db).read(
            demo_a_response_id=demo_a_response_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_RESPONSE_RETRIEVED
        )
    except (
        DemoAResponseNotFoundException,
        DemoAResponsePermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Get all DemoAResponses by demo_a_id
@router.get(
    "/demo-a-response/by-demo-a/{demo_a_id}/", response_model=ApiResponseSchema[list[DemoAResponseReadSchema]]
)
async def get_demo_a_responses_by_demo_a_id(
    demo_a_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve all demo A responses for a specific demo_a_id."""

    try:
        data = await DemoAResponseService(db).get_by_demo_a_id(
            demo_a_id=demo_a_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[list[DemoAResponseReadSchema]](
            success=True, data=data, message=SuccessMessages.DEMO_A_RESPONSES_RETRIEVED
        )
    except (
        DemoAResponsePermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all DemoAResponses
@router.get("/demo-a-responses/", response_model=PaginatedResponseSchema[list[DemoAResponseReadSchema]])
async def list_demo_a_responses(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all demo A responses."""
    try:
        # Use filters directly (already parsed in get_list_params)
        result = await DemoAResponseService(db).list_all(
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

        return PaginatedResponseSchema[list[DemoAResponseReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.DEMO_A_RESPONSES_RETRIEVED,
        )
    except (DemoAResponsePermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update a DemoAResponse
@router.patch(
    "/demo-a-response/update/{demo_a_response_id}/", response_model=ApiResponseSchema[DemoAResponseReadSchema]
)
async def update_demo_a_response(
    demo_a_response_id: UUID,
    payload: DemoAResponseUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing demo A response.

    This endpoint allows updating demo A response fields.
    """
    try:
        # Update demo A response using the schema
        data = await DemoAResponseService(db).update(
            demo_a_response_id=demo_a_response_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return ApiResponseSchema[DemoAResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_RESPONSE_UPDATED
        )

    except (
        DemoAResponseNotFoundException,
        DemoAResponseUpdateException,
        DemoAResponseInvalidDataException,
        DemoAResponsePermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_UPDATE_FAILED}: {str(e)}",
        ) from e


# Update is_active of a DemoAResponse
@router.patch(
    "/demo-a-response/update/is-active/{demo_a_response_id}/",
    response_model=ApiResponseSchema[DemoAResponseReadSchema],
)
async def update_demo_a_response_is_active(
    demo_a_response_id: UUID,
    payload: DemoAResponseIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo A response is_active status.

    Updates only the is_active field of the demo A response.
    """
    try:
        data = await DemoAResponseService(db).update_is_active(
            demo_a_response_id=demo_a_response_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return ApiResponseSchema[DemoAResponseReadSchema](
            success=True,
            data=data,
            message=SuccessMessages.DEMO_A_RESPONSE_ACTIVE_STATUS_UPDATED,
        )
    except (
        DemoAResponseNotFoundException,
        DemoAResponseUpdateException,
        DemoAResponsePermissionDeniedException,
        DemoAResponseInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e

# Update DemoAResponse status
@router.patch(
    "/demo-a-response/update/status/{demo_a_response_id}/",
    response_model=ApiResponseSchema[DemoAResponseReadSchema],
)
async def update_demo_a_response_status(
    demo_a_response_id: UUID,
    payload: DemoAResponseStatusUpdateSchema,  # Use the correct schema
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo A response status and error messages.

    Updates the demo A response status, error_message, and error_user_message fields.
    """
    try:
        data = await DemoAResponseService(db).update_status(
            demo_a_response_id=demo_a_response_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return ApiResponseSchema[DemoAResponseReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_RESPONSE_STATUS_UPDATED
        )
    except (
        DemoAResponseNotFoundException,
        DemoAResponseUpdateException,
        DemoAResponsePermissionDeniedException,
        DemoAResponseInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e

# Delete a DemoAResponse
@router.delete("/demo-a-response/delete/{demo_a_response_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo_a_response(
    demo_a_response_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete a demo A response by ID."""
    try:
        await DemoAResponseService(db).delete(
            demo_a_response_id=demo_a_response_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_A_RESPONSE_DELETED
        )
    except (
        DemoAResponseNotFoundException,
        DemoAResponseDeletionException,
        DemoAResponsePermissionDeniedException,
        DemoAResponseInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_RESPONSE_DELETION_FAILED}: {str(e)}",
        ) from e