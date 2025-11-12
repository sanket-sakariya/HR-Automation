from __future__ import annotations
from sqlalchemy import Table, Column, String, MetaData, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.logger_config import logger
from app.exception.baseapp_exception import InternalServerErrorException
from app.config.constants import DatabaseErrorMessages
from app.repository.baseapp_repository import BaseAppRepository
from app.model.migration_model import MigrationModel


class MigrationRepository(BaseAppRepository[MigrationModel]):
    """Repository for migration-related database operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize migration repository.
        
        Args:
            db: The asynchronous database session.
        """
        super().__init__(db, MigrationModel)
        self.db = db
        
        # Define alembic_version table structure
        self.metadata = MetaData()
        self.alembic_version_table = Table(
            'alembic_version',
            self.metadata,
            Column('version_num', String, primary_key=True),
            schema='public'
        )
    
    async def check_alembic_version_table_exists(self) -> bool:
        """
        Check if the alembic_version table exists in the database.
        
        Returns:
            True if the table exists, False otherwise
        """
        try:
            def check_table(sync_conn):
                inspector = inspect(sync_conn)
                return 'alembic_version' in inspector.get_table_names(schema='public')
            
            table_exists = await self.db.run_sync(check_table)
            return table_exists
        except Exception as e:
            logger.error(f"Error checking alembic_version table existence: {str(e)}")
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DATA_RETRIEVAL_ERROR}: {str(e)}"
            ) from e
    
    async def get_current_revision(self) -> str:
        """Get the current revision of the database."""
        if not await self.check_alembic_version_table_exists():
            return ""
        
        query = text(f"SELECT version_num FROM {self.alembic_version_table.name}")
        result = await self.db.execute(query)
        revision = result.scalar_one_or_none()
        return revision or ""