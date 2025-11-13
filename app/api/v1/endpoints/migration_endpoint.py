from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db
from app.schema.migration_schema import (
    MigrationResponseSchema,
    RevisionRequestSchema,
)
from app.schema.response_schema import ApiResponseSchema
from app.service.migration_service import MigrationService


router = APIRouter()


def get_migration_service() -> MigrationService:
    """Get the migration service."""
    return MigrationService()


@router.post(
    "/migration/revision",
    response_model=ApiResponseSchema[MigrationResponseSchema],
)
async def create_revision(
    request: RevisionRequestSchema,
    migration_service: MigrationService = Depends(get_migration_service),
):
    """
    Create a new Alembic revision with autogenerate.

    Requires a message in the request body: {"message": "your migration message"}
    """
    result = await migration_service.create_revision(request.message)
    return ApiResponseSchema[MigrationResponseSchema](
        success=True, data=result, message="Revision created successfully"
    )


@router.post(
    "/migration/upgrade",
    response_model=ApiResponseSchema[MigrationResponseSchema],
)
async def upgrade_database(
    migration_service: MigrationService = Depends(get_migration_service),
):
    """
    Upgrade database to the latest revision (head).

    Automatically upgrades to the latest migration without requiring any request body.
    """
    result = await migration_service.upgrade_database()
    return ApiResponseSchema[MigrationResponseSchema](
        success=True,
        data=result,
        message="Database upgrade completed successfully",
    )


@router.post(
    "/migration/upload",
    response_model=ApiResponseSchema[MigrationResponseSchema],
)
async def upload_migrations(
    migration_service: MigrationService = Depends(get_migration_service),
):
    """Upload migration files to Wasabi/S3."""
    result = await migration_service.upload_migrations()
    return ApiResponseSchema[MigrationResponseSchema](
        success=True,
        data=result,
        message="Migration upload completed successfully",
    )


@router.post(
    "/migration/download",
    response_model=ApiResponseSchema[MigrationResponseSchema],
)
async def download_migrations(
    migration_service: MigrationService = Depends(get_migration_service),
):
    """Download migration files from Wasabi/S3."""
    result = await migration_service.download_migrations()
    return ApiResponseSchema[MigrationResponseSchema](
        success=True,
        data=result,
        message="Migration download completed successfully",
    )