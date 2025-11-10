from __future__ import annotations
from typing import Optional
from sqlalchemy import Table, Column, String, MetaData, select, inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config.database import async_engine
from app.config.logger_config import logger
from app.exception.baseapp_exception import InternalServerErrorException
from app.config.constants import DatabaseErrorMessages


class MigrationRepository:
    """Repository for migration-related database operations."""
    
    def __init__(self, engine: Optional[AsyncEngine] = None):
        """
        Initialize migration repository.
        
        Args:
            engine: Optional async engine. Defaults to async_engine from config.
        """
        self.engine = engine or async_engine
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
            async with self.engine.connect() as connection:
                # Use SQLAlchemy inspect to check if table exists
                # For async engines, we need to use run_sync to access the inspector
                def check_table(sync_conn):
                    inspector = inspect(sync_conn)
                    return 'alembic_version' in inspector.get_table_names(schema='public')
                
                table_exists = await connection.run_sync(check_table)
                return table_exists
        except Exception as e:
            logger.error(f"Error checking alembic_version table existence: {str(e)}")
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DATA_RETRIEVAL_ERROR}: {str(e)}"
            ) from e
    
    async def get_current_revision(self) -> Optional[str]:
        """
        Get the current database revision from alembic_version table.
        
        Returns:
            Current revision string if exists, None if table doesn't exist or no revision found
        """
        try:
            # First check if table exists
            table_exists = await self.check_alembic_version_table_exists()
            
            if not table_exists:
                return None
            
            # Get current revision using SQLAlchemy select
            async with self.engine.connect() as connection:
                query = select(self.alembic_version_table.c.version_num).limit(1)
                result = await connection.execute(query)
                revision = result.scalar_one_or_none()
                return revision
        except Exception as e:
            logger.error(f"Error getting current revision: {str(e)}")
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DATA_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

