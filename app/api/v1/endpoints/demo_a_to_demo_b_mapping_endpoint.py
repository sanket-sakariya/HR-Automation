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
from app.service.demo_a_to_demo_b_mapping_service import DemoAToDemoBMappingService


router = APIRouter(route_class=RedisCachedRoute)


@router.post(
    "/mapping/create/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema],
    status_code=status.HTTP_201_CREATED,
)
async def create_mapping(
    payload: DemoAToDemoBMappingCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Create a new mapping between DemoA and DemoB."""
    try:
        data = await DemoAToDemoBMappingService(db).create(
            payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.MAPPING_CREATED
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
            detail=f"{ApiErrorMessages.MAPPING_CREATION_FAILED}: {str(e)}",
        ) from e


@router.get("/mapping/read/{demo_a_to_demo_b_mapping_id}/", response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema])
async def get_mapping(
    demo_a_to_demo_b_mapping_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a mapping by ID."""

    try:
        data = await DemoAToDemoBMappingService(db).read(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.MAPPING_RETRIEVED
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
            detail=f"{ApiErrorMessages.MAPPING_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


@router.get("/mappings/", response_model=PaginatedResponseSchema[list[DemoAToDemoBMappingReadSchema]])
async def list_mappings(
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """List all mappings."""
    try:
        result = await DemoAToDemoBMappingService(db).list_all(
            filters=params.filters,
            search=params.search,
            order_by=params.order_by,
            skip=params.offset,
            limit=params.limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        data = result.get("data", [])
        pagination_data = result.get("pagination", {})

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
            message=SuccessMessages.MAPPINGS_RETRIEVED,
        )
    except (MappingPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.MAPPINGS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


@router.patch(
    "/mapping/update/{demo_a_to_demo_b_mapping_id}/", response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def update_mapping(
    mapping_id: UUID,
    payload: DemoAToDemoBMappingUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Update an existing mapping."""
    try:
        data = await DemoAToDemoBMappingService(db).update(
            mapping_id=mapping_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.MAPPING_UPDATED
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
            detail=f"{ApiErrorMessages.MAPPING_UPDATE_FAILED}: {str(e)}",
        ) from e


@router.delete("/mapping/delete/{demo_a_to_demo_b_mapping_id}/", response_model=ApiResponseSchema[dict])
async def delete_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete a mapping by ID."""
    try:
        await DemoAToDemoBMappingService(db).delete(
            mapping_id=mapping_id, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.MAPPING_DELETED
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
            detail=f"{ApiErrorMessages.MAPPING_DELETION_FAILED}: {str(e)}",
        ) from e

@router.patch(
    "/mapping/update/status/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def update_mapping_status(
    mapping_id: UUID,
    payload: DemoAToDemoBMappingStatusUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Update mapping status and error messages."""
    try:
        data = await DemoAToDemoBMappingService(db).update_status(
            mapping_id=mapping_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.MAPPING_STATUS_UPDATED
        )
    except (MappingNotFoundException, MappingUpdateException, MappingPermissionDeniedException, MappingInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.MAPPING_STATUS_UPDATE_FAILED}: {str(e)}"
        ) from e

@router.patch(
    "/mapping/update/is-active/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema],
)
async def update_mapping_is_active(
    mapping_id: UUID,
    payload: DemoAToDemoBMappingIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Update mapping is_active status."""
    try:
        data = await DemoAToDemoBMappingService(db).update_is_active(
            mapping_id=mapping_id, payload=payload, user_id=user_id, workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.MAPPING_ACTIVE_STATUS_UPDATED
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
            detail=f"{ApiErrorMessages.MAPPING_ACTIVE_STATUS_UPDATE_FAILED}: {str(e)}",
        ) from e
