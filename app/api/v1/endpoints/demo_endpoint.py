from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db as get_db
from app.config.constants import SuccessMessages
from app.schema.response_schema import (
    ApiResponseSchema, 
    PaginatedResponseSchema, 
)
from app.schema.demo_schema import (
    DemoCreateSchema, 
    DemoUpdateSchema, 
    DemoReadSchema,
    DemoStatusUpdateSchema,
    DemoIsActiveUpdateSchema,
    DemoListParamsSchema,
)
from app.service.demo_service import DemoService
from app.exception.demo_exception import (
    DemoNotFoundException,
    DemoCreationException,
    DemoUpdateException,
    DemoDeletionException,
    DemoInvalidDataException,
    DemoPermissionDeniedException
)
from app.exception.baseapp_exception import (

    InternalServerErrorException
)
from app.helper.fastapi.get_header import get_user_id, get_workspace_id

router = APIRouter()

# Create a new demo
@router.post("/", response_model=ApiResponseSchema[DemoReadSchema], status_code=status.HTTP_201_CREATED)
async def create_demo(
    demo_in: DemoCreateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Create a new demo.
    """
    try:
        data = await DemoService(db).create(payload=demo_in, user_id=user_id, workspace_id=workspace_id)
        return ApiResponseSchema[DemoReadSchema](success=True, data=data, message=SuccessMessages.DEMO_CREATED)
    except (DemoCreationException, DemoInvalidDataException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

# Retrieve a demo by ID
@router.get("/{demo_id}/", response_model=ApiResponseSchema[DemoReadSchema])
async def get_demo(
    demo_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Retrieve a demo by ID.
    """
    try:
        data = await DemoService(db).read(demo_id=demo_id, user_id=user_id, workspace_id=workspace_id)
        return ApiResponseSchema[DemoReadSchema](success=True, data=data, message=SuccessMessages.DEMO_RETRIEVED)
    except (DemoNotFoundException, DemoPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

# List all demos
@router.get("/", response_model=PaginatedResponseSchema[List[DemoReadSchema]])
async def list_demos(
    params: DemoListParamsSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    List all demos.
    """
    try:
        result = await DemoService(db).list_all(
            filters=params.filters,
            search=params.search,
            order_by=params.order_by,
            skip=params.offset,
            limit=params.limit,
            user_id=user_id,
            workspace_id=workspace_id
        )
        return PaginatedResponseSchema[List[DemoReadSchema]](
            success=True, 
            data=result.get("data", []), 
            pagination=result.get("pagination", {}),
            message=SuccessMessages.DEMO_RETRIEVED
        )
    except (DemoPermissionDeniedException, InternalServerErrorException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

# Update an existing demo
@router.patch("/{demo_id}/", response_model=ApiResponseSchema[DemoReadSchema])
async def update_demo(
    demo_id: UUID,
    demo_in: DemoUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update an existing demo.
    """
    try:
        data = await DemoService(db).update(demo_id=demo_id, payload=demo_in, user_id=user_id, workspace_id=workspace_id)
        return ApiResponseSchema[DemoReadSchema](success=True, data=data, message=SuccessMessages.DEMO_UPDATED)
    except (DemoNotFoundException, DemoUpdateException, DemoInvalidDataException, DemoPermissionDeniedException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

# Delete a demo
@router.delete("/{demo_id}/", response_model=ApiResponseSchema[dict])
async def delete_demo(
    demo_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Delete a demo by ID.
    """
    try:
        await DemoService(db).delete(demo_id=demo_id, user_id=user_id, workspace_id=workspace_id)
        return ApiResponseSchema[dict](success=True, data={}, message=SuccessMessages.DEMO_DELETED)
    except (DemoNotFoundException, DemoDeletionException, DemoPermissionDeniedException, DemoInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

# Update demo status
@router.patch("/status/{demo_id}/", response_model=ApiResponseSchema[DemoReadSchema])
async def update_demo_status(
    demo_id: UUID,
    payload: DemoStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo status and error messages.
    """
    try:
        data = await DemoService(db).update_status(demo_id=demo_id, payload=payload, user_id=user_id, workspace_id=workspace_id)
        return ApiResponseSchema[DemoReadSchema](success=True, data=data, message=SuccessMessages.DEMO_STATUS_UPDATED)
    except (DemoNotFoundException, DemoUpdateException, DemoPermissionDeniedException, DemoInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

# Update demo is_active status
@router.patch("/is-active/{demo_id}/", response_model=ApiResponseSchema[DemoReadSchema])
async def update_demo_is_active(
    demo_id: UUID,
    payload: DemoIsActiveUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_user_id),
    workspace_id: UUID = Depends(get_workspace_id),
):
    """
    Update demo is_active status.
    """
    try:
        data = await DemoService(db).update_is_active(demo_id=demo_id, payload=payload, user_id=user_id, workspace_id=workspace_id)
        return ApiResponseSchema[DemoReadSchema](success=True, data=data, message=SuccessMessages.DEMO_ACTIVE_STATUS_UPDATED)
    except (DemoNotFoundException, DemoUpdateException, DemoPermissionDeniedException, DemoInvalidDataException) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e