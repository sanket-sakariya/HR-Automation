from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import ApiErrorMessages, SuccessMessages
from app.config.database import get_async_db
from app.exception.baseapp_exception import InternalServerErrorException
from app.exception.demo_exception import (
    DemoCreationException,
    DemoDeletionException,
    DemoInvalidDataException,
    DemoNotFoundException,
    DemoPermissionDeniedException,
    DemoUpdateException,
)
from app.helper.fastapi.get_header import (
    ListParamsSchema,
    get_list_params,
    get_user_id,
    get_workspace_id,
)
from app.schema.demo_schema import (
    DemoCreateSchema,
    DemoIsActiveUpdateSchema,
    DemoReadSchema,
    DemoUpdateSchema,
)
from app.schema.response_schema import (
    ApiResponseSchema,
    PaginatedResponseSchema,
    PaginationMeta,
)
from app.service.demo_service import DemoService


router = APIRouter()


# Create a new Demo
@router.post(
    "/demo/create/",
    response_model=ApiResponseSchema[DemoReadSchema],
    status_code=status.HTTP_201_CREATED,
)
async def create_demo(
    payload: DemoCreateSchema,
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
        data = await DemoService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_CREATED
        )

    except (
        DemoCreationException, 
        DemoInvalidDataException, 
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve an Demo by ID
@router.get("/demo/read/{demo_id}/", response_model=ApiResponseSchema[DemoReadSchema])
async def get_demo(
    demo_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve an demo by ID."""

    try:
        data = await DemoService(db).read(
            demo_id=demo_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_RETRIEVED
        )
    except (
        DemoNotFoundException,
        DemoPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all Demos
@router.get("/demos/", response_model=PaginatedResponseSchema[list[DemoReadSchema]])
async def list_demos(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all demos."""
    try:
        # Use filters directly (already parsed in get_list_params)
        result = await DemoService(db).list_all(
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

        return PaginatedResponseSchema[list[DemoReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.DEMOS_RETRIEVED,
        )
    except (DemoPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMOS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update an Demo
@router.patch(
    "/demo/update/{demo_id}/", response_model=ApiResponseSchema[DemoReadSchema]
)
async def update_demo(
    demo_id: UUID,
    payload: DemoUpdateSchema,
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
        data = await DemoService(db).update(
            demo_id=demo_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_UPDATED
        )

    except (
        DemoNotFoundException,
        DemoUpdateException,
        DemoInvalidDataException,
        DemoPermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_UPDATE_FAILED}: {str(e)}",
        ) from e


# Delete an Demo
@router.delete("/demo/delete/{demo_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo(
    demo_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete an demo by ID."""
    try:
        await DemoService(db).delete(
            demo_id=demo_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_DELETED
        )
    except (
        DemoNotFoundException,
        DemoDeletionException,
        DemoPermissionDeniedException,
        DemoInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_DELETION_FAILED}: {str(e)}",
        ) from e


# Update is_active of an Demo
@router.patch(
    "/demo/update/is-active/{demo_id}/",
    response_model=ApiResponseSchema[DemoReadSchema],
)
async def update_demo_is_active(
    demo_id: UUID,
    payload: DemoIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo is_active status.

    Updates only the is_active field of the demo.
    """
    try:
        data = await DemoService(db).update_is_active(
            demo_id=demo_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_ACTIVE_STATUS_UPDATED
        )
    except (
        DemoNotFoundException,
        DemoUpdateException,
        DemoPermissionDeniedException,
        DemoInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e