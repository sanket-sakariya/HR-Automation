from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db

from app.config.constants import SuccessMessages, ApiErrorMessages

from app.helper.fastapi.get_header import get_list_params, get_user_id, get_workspace_id

from app.schema.response_schema import (
    ApiResponseSchema, 
    PaginatedResponseSchema, 
    PaginationMeta,
    ListParamsSchema
)

from app.schema.demo_b_schema import (
    DemoBCreateSchema, 
    DemoBUpdateSchema, 
    DemoBReadSchema,
    DemoBStatusUpdateSchema,
    DemoBIsActiveUpdateSchema
)

from app.service.demo_b_service import DemoBService

from app.exception.demo_b_exception import (
    DemoBNotFoundException,
    DemoBCreationException,
    DemoBUpdateException,
    DemoBDeletionException,
    DemoBInvalidDataException,
    DemoBPermissionDeniedException
)

from app.exception.baseapp_exception import (
    InternalServerErrorException
)

router = APIRouter()


# Create a new DemoB
@router.post(
    "/demo-b/create/",
    response_model=ApiResponseSchema[DemoBReadSchema],
    status_code=http_status.HTTP_201_CREATED,
)
async def create_demo_b(
    payload: DemoBCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Create a new demo B.

    This endpoint allows creating a demo B.
    """
    try:
        # Create demo using the schema
        data = await DemoBService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoBReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_CREATED
        )

    except (
        DemoBCreationException, 
        DemoBInvalidDataException, 
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve an DemoB by ID
@router.get("/demo-b/read/{demo_b_id}/", response_model=ApiResponseSchema[DemoBReadSchema])
async def get_demo_b(
    demo_b_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a demo B by ID."""

    try:
        data = await DemoBService(db).read(
            demo_b_id=demo_b_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoBReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_RETRIEVED
        )
    except (
        DemoBNotFoundException,
        DemoBPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all DemoBs
@router.get("/demo-bs/", response_model=PaginatedResponseSchema[list[DemoBReadSchema]])
async def list_demo_bs(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all demo Bs."""
    try:
        # Use filters directly (already parsed in get_list_params)
        result = await DemoBService(db).list_all(
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

        return PaginatedResponseSchema[list[DemoBReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.DEMO_B_RETRIEVED,
        )
    except (DemoBPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update an DemoB
@router.patch(
    "/demo-b/update/{demo_b_id}/", response_model=ApiResponseSchema[DemoBReadSchema]
)
async def update_demo_b(
    demo_b_id: UUID,
    payload: DemoBUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing demo B.

    This endpoint allows updating demo B fields.
    """
    try:
        # Update demo using the schema
        data = await DemoBService(db).update(
            demo_b_id=demo_b_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoBReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_UPDATED
        )

    except (
        DemoBNotFoundException,
        DemoBUpdateException,
        DemoBInvalidDataException,
        DemoBPermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_UPDATE_FAILED}: {str(e)}",
        ) from e


# Delete an DemoB
@router.delete("/demo-b/delete/{demo_b_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo_b(
    demo_b_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete a demo B by ID."""
    try:
        await DemoBService(db).delete(
            demo_b_id=demo_b_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_B_DELETED
        )
    except (
        DemoBNotFoundException,
        DemoBDeletionException,
        DemoBPermissionDeniedException,
        DemoBInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_DELETION_FAILED}: {str(e)}",
        ) from e

# Update DemoB status
@router.patch(
    "/demo-b/update/status/{demo_b_id}/", 
    response_model=ApiResponseSchema[DemoBReadSchema]
)
async def update_demo_b_status(
    demo_b_id: UUID,
    payload: DemoBStatusUpdateSchema,  # Use the correct schema
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo B status and error messages.
    
    Updates the demo B status, error_message, and error_user_message fields.
    """
    try:
        data = await DemoBService(db).update_status(
            demo_b_id=demo_b_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoBReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_STATUS_UPDATED
        )
    except (DemoBNotFoundException, DemoBUpdateException, DemoBPermissionDeniedException, DemoBInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_STATUS_UPDATE_FAILED}: {str(e)}"
        ) from e

# Update is_active of an DemoB
@router.patch(
    "/demo-b/update/is-active/{demo_b_id}/",
    response_model=ApiResponseSchema[DemoBReadSchema],
)
async def update_demo_b_is_active(
    demo_b_id: UUID,
    payload: DemoBIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo B is_active status.

    Updates only the is_active field of the demo B.
    """
    try:
        data = await DemoBService(db).update_is_active(
            demo_b_id=demo_b_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoBReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_B_ACTIVE_STATUS_UPDATED
        )
    except (
        DemoBNotFoundException,
        DemoBUpdateException,
        DemoBPermissionDeniedException,
        DemoBInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_B_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e
