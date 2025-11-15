from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.helper.redis_cached_route_helper import RedisCachedRoute

from app.config.constants import ApiErrorMessages, SuccessMessages
from app.config.database import get_async_db
from app.exception.baseapp_exception import InternalServerErrorException
from app.exception.demo_a_exception import (
    DemoACreationException,
    DemoADeletionException,
    DemoAInvalidDataException,
    DemoANotFoundException,
    DemoAPermissionDeniedException,
    DemoAUpdateException,
)
from app.helper.fastapi.get_header import (
    ListParamsSchema,
    get_list_params,
    get_user_id,
    get_workspace_id,
)
from app.schema.demo_a_schema import (
    DemoACreateSchema,
    DemoAIsActiveUpdateSchema,
    DemoAReadSchema,
    DemoAUpdateSchema,
    DemoAStatusUpdateSchema
)
from app.schema.response_schema import (
    ApiResponseSchema,
    PaginatedResponseSchema,
    PaginationMeta,
)
from app.service.demo_a_service import DemoAService


# Use RedisCachedRoute for automatic caching at route level
router = APIRouter(route_class=RedisCachedRoute)


# Create a new DemoA
@router.post(
    "/demo-a/create/",
    response_model=ApiResponseSchema[DemoAReadSchema],
    status_code=status.HTTP_201_CREATED,
)
async def create_demo(
    payload: DemoACreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Create a new demo.

    This endpoint allows creating a demo.
    """
    try:
        # Create demo using the schema
        data = await DemoAService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_CREATED
        )

    except (
        DemoACreationException, 
        DemoAInvalidDataException, 
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve an DemoA by ID
@router.get("/demo-a/read/{demo_a_id}/", response_model=ApiResponseSchema[DemoAReadSchema])
async def get_demo(
    demo_a_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve an demo by ID."""

    try:
        data = await DemoAService(db).read(
            demo_a_id=demo_a_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_RETRIEVED
        )
    except (
        DemoANotFoundException,
        DemoAPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all DemoAs
@router.get("/demos/", response_model=PaginatedResponseSchema[list[DemoAReadSchema]])
async def list_demos(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all demos."""
    try:
        # Use filters directly (already parsed in get_list_params)
        result = await DemoAService(db).list_all(
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

        return PaginatedResponseSchema[list[DemoAReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.DEMOS_RETRIEVED,
        )
    except (DemoAPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMOS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update an DemoA
@router.patch(
    "/demo-a/update/{demo_a_id}/", response_model=ApiResponseSchema[DemoAReadSchema]
)
async def update_demo(
    demo_a_id: UUID,
    payload: DemoAUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing demo.

    This endpoint allows updating demo fields.
    """
    try:
        # Update demo using the schema
        data = await DemoAService(db).update(
            demo_a_id=demo_a_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_UPDATED
        )

    except (
        DemoANotFoundException,
        DemoAUpdateException,
        DemoAInvalidDataException,
        DemoAPermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_UPDATE_FAILED}: {str(e)}",
        ) from e


# Delete an DemoA
@router.delete("/demo-a/delete/{demo_a_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo(
    demo_a_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete an demo by ID."""
    try:
        await DemoAService(db).delete(
            demo_a_id=demo_a_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_DELETED
        )
    except (
        DemoANotFoundException,
        DemoADeletionException,
        DemoAPermissionDeniedException,
        DemoAInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_DELETION_FAILED}: {str(e)}",
        ) from e

# Update DemoA status
@router.patch(
    "/demo-a/update/status/{demo_a_id}/", 
    response_model=ApiResponseSchema[DemoAReadSchema]
)
async def update_demo_status(
    demo_a_id: UUID,
    payload: DemoAStatusUpdateSchema,  # Use the correct schema
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo status and error messages.
    
    Updates the demo status, error_message, and error_user_message fields.
    """
    try:
        data = await DemoAService(db).update_status(
            demo_a_id=demo_a_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_STATUS_UPDATED
        )
    except (DemoANotFoundException, DemoAUpdateException, DemoAPermissionDeniedException, DemoAInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_STATUS_UPDATE_FAILED}: {str(e)}"
        ) from e

# Update is_active of an DemoA
@router.patch(
    "/demo-a/update/is-active/{demo_a_id}/",
    response_model=ApiResponseSchema[DemoAReadSchema],
)
async def update_demo_is_active(
    demo_a_id: UUID,
    payload: DemoAIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo is_active status.

    Updates only the is_active field of the demo.
    """
    try:
        data = await DemoAService(db).update_is_active(
            demo_a_id=demo_a_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_ACTIVE_STATUS_UPDATED
        )
    except (
        DemoANotFoundException,
        DemoAUpdateException,
        DemoAPermissionDeniedException,
        DemoAInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e
