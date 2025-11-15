"""API endpoints for database backup and restore operations."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schema.backup_schema import (
    BackupCreateRequestSchema,
    BackupCreateResponseSchema,
    BackupListResponseSchema,
    BackupRestoreRequestSchema,
    BackupRestoreResponseSchema,
)
from app.schema.response_schema import ApiResponseSchema
from app.service.backup_service import BackupService


router = APIRouter()


@router.post(
    "/backup/create",
    response_model=ApiResponseSchema[BackupCreateResponseSchema],
)
async def create_backup():
    """Create a database backup and upload to Wasabi."""
    try:
        result = await BackupService().create_backup(
            backup_name=None,
            description=None
        )
        return ApiResponseSchema[BackupCreateResponseSchema](
            success=True,
            data=result,
            message="Database backup created and uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(e)}"
        ) from e


@router.get(
    "/backup/list",
    response_model=ApiResponseSchema[BackupListResponseSchema],
)
async def list_backups():
    """List all available database backups from Wasabi."""
    try:
        result = await BackupService().list_backups()
        return ApiResponseSchema[BackupListResponseSchema](
            success=True,
            data=result,
            message=f"Found {result.count} backup(s)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backups: {str(e)}"
        ) from e


@router.post(
    "/backup/restore",
    response_model=ApiResponseSchema[BackupRestoreResponseSchema],
)
async def restore_backup(
    payload: BackupRestoreRequestSchema,
):
    """
    Restore database from a backup file.
    
    WARNING: This will overwrite the current database.
    """
    try:
        result = await BackupService().restore_backup(
            backup_filename=payload.backup_filename
        )
        return ApiResponseSchema[BackupRestoreResponseSchema](
            success=True,
            data=result,
            message="Database restored successfully from backup"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup restore failed: {str(e)}"
        ) from e
