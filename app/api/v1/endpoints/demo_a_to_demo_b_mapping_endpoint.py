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

from app.schema.demo_a_to_demo_b_mapping_schema import (
    DemoAToDemoBMappingCreateSchema, 
    DemoAToDemoBMappingUpdateSchema, 
    DemoAToDemoBMappingReadSchema,
    DemoAToDemoBMappingStatusUpdateSchema,
    DemoAToDemoBMappingIsActiveUpdateSchema
)

from app.service.demo_a_to_demo_b_mapping_service import DemoAToDemoBMappingService

from app.exception.demo_a_to_demo_b_mapping_exception import (
    DemoAToDemoBMappingNotFoundException,
    DemoAToDemoBMappingCreationException,
    DemoAToDemoBMappingUpdateException,
    DemoAToDemoBMappingDeletionException,
    DemoAToDemoBMappingInvalidDataException,
    DemoAToDemoBMappingPermissionDeniedException
)

from app.exception.demo_a_exception import DemoANotFoundException

from app.exception.demo_b_exception import DemoBNotFoundException

from app.exception.baseapp_exception import (
    InternalServerErrorException
)

router = APIRouter()


@router.post(
    "/demo-a-to-demo-b-mapping/create/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema],
    status_code=http_status.HTTP_201_CREATED,
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
            success=True, data=data, message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPING_CREATED
        )

    except (
        DemoANotFoundException,
        DemoBNotFoundException,
        DemoAToDemoBMappingCreationException,
        DemoAToDemoBMappingInvalidDataException,
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_CREATION_FAILED}: {str(e)}",
        ) from e


@router.get(
    "/demo-a-to-demo-b-mapping/read/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def get_mapping(
    demo_a_to_demo_b_mapping_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Retrieve a mapping by ID."""

    try:
        data = await DemoAToDemoBMappingService(db).read(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPING_RETRIEVED
        )
    except (
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingPermissionDeniedException,
        InternalServerErrorException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


@router.get(
    "/demo-a-to-demo-b-mappings/",
    response_model=PaginatedResponseSchema[list[DemoAToDemoBMappingReadSchema]]
)
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
            message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPINGS_RETRIEVED,
        )
    except (DemoAToDemoBMappingPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPINGS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


@router.patch(
    "/demo-a-to-demo-b-mapping/update/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def update_mapping(
    demo_a_to_demo_b_mapping_id: UUID,
    payload: DemoAToDemoBMappingUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Update an existing mapping."""
    try:
        data = await DemoAToDemoBMappingService(db).update(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id
        )

        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPING_UPDATED
        )

    except (
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingUpdateException,
        DemoAToDemoBMappingInvalidDataException,
        DemoAToDemoBMappingPermissionDeniedException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_UPDATE_FAILED}: {str(e)}",
        ) from e


@router.delete(
    "/demo-a-to-demo-b-mapping/delete/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[dict]
)
async def delete_mapping(
    demo_a_to_demo_b_mapping_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete a mapping by ID."""
    try:
        await DemoAToDemoBMappingService(db).delete(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True, data={}, message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETED
        )
    except (
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingDeletionException,
        DemoAToDemoBMappingPermissionDeniedException,
        DemoAToDemoBMappingInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETION_FAILED}: {str(e)}",
        ) from e

@router.patch(
    "/demo-a-to-demo-b-mapping/update/status/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema]
)
async def update_mapping_status(
    demo_a_to_demo_b_mapping_id: UUID,
    payload: DemoAToDemoBMappingStatusUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Update mapping status and error messages."""
    try:
        data = await DemoAToDemoBMappingService(db).update_status(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True, data=data, message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPING_STATUS_UPDATED
        )
    except (
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingUpdateException,
        DemoAToDemoBMappingPermissionDeniedException,
        DemoAToDemoBMappingInvalidDataException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_STATUS_UPDATE_FAILED}: {str(e)}"
        ) from e

@router.patch(
    "/demo-a-to-demo-b-mapping/update/is-active/{demo_a_to_demo_b_mapping_id}/",
    response_model=ApiResponseSchema[DemoAToDemoBMappingReadSchema],
)
async def update_mapping_is_active(
    demo_a_to_demo_b_mapping_id: UUID,
    payload: DemoAToDemoBMappingIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Update mapping is_active status."""
    try:
        data = await DemoAToDemoBMappingService(db).update_is_active(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            payload=payload,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return ApiResponseSchema[DemoAToDemoBMappingReadSchema](
            success=True,
            data=data,
            message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPING_ACTIVE_STATUS_UPDATED
        )
    except (
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingUpdateException,
        DemoAToDemoBMappingPermissionDeniedException,
        DemoAToDemoBMappingInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_ACTIVE_STATUS_UPDATE_FAILED}: "
                f"{str(e)}"
            ),
        ) from e


@router.get(
    "/demo-a-to-demo-b-mapping/by-demo-a/{demo_a_id}/",
    response_model=PaginatedResponseSchema[list[DemoAToDemoBMappingReadSchema]]
)
async def get_mappings_by_demo_a_id(
    demo_a_id: UUID,
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Get all mappings for a specific demo_a_id."""
    try:
        result = await DemoAToDemoBMappingService(db).get_by_demo_a_id(
            demo_a_id=demo_a_id,
            workspace_id=workspace_id,
            skip=params.offset,
            limit=params.limit,
            user_id=user_id
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
            message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPINGS_RETRIEVED,
        )
    except (
        DemoANotFoundException,
        DemoAToDemoBMappingPermissionDeniedException,
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPINGS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


@router.get(
    "/demo-a-to-demo-b-mapping/by-demo-b/{demo_b_id}/",
    response_model=PaginatedResponseSchema[list[DemoAToDemoBMappingReadSchema]]
)
async def get_mappings_by_demo_b_id(
    demo_b_id: UUID,
    params: ListParamsSchema = Depends(get_list_params),
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Get all mappings for a specific demo_b_id."""
    try:
        result = await DemoAToDemoBMappingService(db).get_by_demo_b_id(
            demo_b_id=demo_b_id,
            workspace_id=workspace_id,
            skip=params.offset,
            limit=params.limit,
            user_id=user_id
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
            message=SuccessMessages.DEMO_A_TO_DEMO_B_MAPPINGS_RETRIEVED,
        )
    except (
        DemoBNotFoundException,
        DemoAToDemoBMappingPermissionDeniedException,
        InternalServerErrorException
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPINGS_RETRIEVAL_FAILED}: {str(e)}",
        ) from e


@router.delete(
    "/demo-a-to-demo-b-mapping/delete-by-demo-a/{demo_a_id}/",
    response_model=ApiResponseSchema[dict]
)
async def delete_mappings_by_demo_a_id(
    demo_a_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete all mappings for a specific demo_a_id."""
    try:
        deleted_count = await DemoAToDemoBMappingService(db).delete_by_demo_a_id(
            demo_a_id=demo_a_id,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True,
            data={"deleted_count": deleted_count},
            message=f"{deleted_count} mapping(s) deleted successfully"
        )
    except (
        DemoANotFoundException,
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingDeletionException,
        DemoAToDemoBMappingPermissionDeniedException,
        DemoAToDemoBMappingInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETION_FAILED}: {str(e)}",
        ) from e


@router.delete(
    "/demo-a-to-demo-b-mapping/delete-by-demo-b/{demo_b_id}/",
    response_model=ApiResponseSchema[dict]
)
async def delete_mappings_by_demo_b_id(
    demo_b_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """Delete all mappings for a specific demo_b_id."""
    try:
        deleted_count = await DemoAToDemoBMappingService(db).delete_by_demo_b_id(
            demo_b_id=demo_b_id,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return ApiResponseSchema[dict](
            success=True,
            data={"deleted_count": deleted_count},
            message=f"{deleted_count} mapping(s) deleted successfully"
        )
    except (
        DemoBNotFoundException,
        DemoAToDemoBMappingNotFoundException,
        DemoAToDemoBMappingDeletionException,
        DemoAToDemoBMappingPermissionDeniedException,
        DemoAToDemoBMappingInvalidDataException,
    ) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{ApiErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETION_FAILED}: {str(e)}",
        ) from e
