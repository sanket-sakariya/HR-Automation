from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.helper.redis_cached_route_helper import RedisCachedRoute

from app.config.constants import ApiErrorMessages, SuccessMessages
from app.config.database import get_async_db
from app.exception.baseapp_exception import InternalServerErrorException
from app.exception.demo_a_to_demo_b_mapping_exception import (
    MappingCreationException,
    MappingDeletionException,
    MappingInvalidDataException,
    MappingNotFoundException,
    MappingPermissionDeniedException,
    MappingUpdateException,
)
from app.helper.fastapi.get_header import (
    ListParamsSchema,
    get_list_params,
    get_user_id,
    get_workspace_id,
)
from app.schema.demo_a_to_demo_b_mapping_schema import (
    DemoAToDemoBMappingCreateSchema,
    DemoAToDemoBMappingIsActiveUpdateSchema,
    DemoAToDemoBMappingReadSchema,
    DemoAToDemoBMappingUpdateSchema,
    DemoAToDemoBMappingStatusUpdateSchema
)
from app.schema.response_schema import (
    ApiResponseSchema,
    PaginatedResponseSchema,
    PaginationMeta,
)
from app.service.demo_a_to_demo_b_mapping_service import MappingAToMappingBMappingService


# Use RedisCachedRoute for automatic caching at route level
router = APIRouter(route_class=RedisCachedRoute)


# Create a new Mapping
@router.post(
    "/mapping/create/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema],
    status_code=status.HTTP_201_CREATED,
)
async def create_demo(
    payload: DemoAToDemoBMappingCreateSchema,
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
        data = await MappingAToMappingBMappingService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_CREATED
        )

    except (
        MappingCreationException, 
        MappingInvalidDataException, 
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_CREATION_FAILED}: {str(e)}",
        ) from e


# Retrieve an Mapping by ID
@router.get("/mapping/read/{mapping_id}/", response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema])
async def get_demo(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve an demo by ID."""

    try:
        data = await MappingAToMappingBMappingService(db).read(
            mapping_id=mapping_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_RETRIEVED
        )
    except (
        MappingNotFoundException,
        MappingPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# List all Mappings
@router.get("/demos/", response_model=PaginatedResponseSchema[list[DemoAToDemoBMappingReadSchema]])
async def list_demos(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all demos."""
    try:
        # Use filters directly (already parsed in get_list_params)
        result = await MappingAToMappingBMappingService(db).list_all(
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

        return PaginatedResponseSchema[list[DemoAToDemoBMappingReadSchema]](
            success=True,
            data=data,
            pagination=pagination,
            message=SuccessMessages.DEMOS_RETRIEVED,
        )
    except (MappingPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMOS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


# Update an Mapping
@router.patch(
    "/mapping/update/{mapping_id}/", response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def update_demo(
    mapping_id: UUID,
    payload: DemoAToDemoBMappingUpdateSchema,
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
        data = await MappingAToMappingBMappingService(db).update(
            mapping_id=mapping_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_UPDATED
        )

    except (
        MappingNotFoundException,
        MappingUpdateException,
        MappingInvalidDataException,
        MappingPermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_UPDATE_FAILED}: {str(e)}",
        ) from e


# Delete an Mapping
@router.delete("/mapping/delete/{mapping_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete an demo by ID."""
    try:
        await MappingAToMappingBMappingService(db).delete(
            mapping_id=mapping_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_DELETED
        )
    except (
        MappingNotFoundException,
        MappingDeletionException,
        MappingPermissionDeniedException,
        MappingInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_DELETION_FAILED}: {str(e)}",
        ) from e

# Update Mapping status
@router.patch(
    "/mapping/update/status/{mapping_id}/", 
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def update_demo_status(
    mapping_id: UUID,
    payload: DemoAToDemoBMappingStatusUpdateSchema,  # Use the correct schema
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo status and error messages.
    
    Updates the demo status, error_message, and error_user_message fields.
    """
    try:
        data = await MappingAToMappingBMappingService(db).update_status(
            mapping_id=mapping_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_STATUS_UPDATED
        )
    except (MappingNotFoundException, MappingUpdateException, MappingPermissionDeniedException, MappingInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_STATUS_UPDATE_FAILED}: {str(e)}"
        ) from e

# Update is_active of an Mapping
@router.patch(
    "/mapping/update/is-active/{mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema],
)
async def update_demo_is_active(
    mapping_id: UUID,
    payload: DemoAToDemoBMappingIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo is_active status.

    Updates only the is_active field of the demo.
    """
    try:
        data = await MappingAToMappingBMappingService(db).update_is_active(
            mapping_id=mapping_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_ACTIVE_STATUS_UPDATED
        )
    except (
        MappingNotFoundException,
        MappingUpdateException,
        MappingPermissionDeniedException,
        MappingInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e
