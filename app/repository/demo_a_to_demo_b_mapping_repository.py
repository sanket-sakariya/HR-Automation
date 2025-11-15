from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.demo_a_to_demo_b_mapping_model import DemoAToDemoBMappingModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.demo_a_to_demo_b_mapping_exception import (
    DemoAToDemoBMappingNotFoundException,
)
from app.exception.baseapp_exception import InternalServerErrorException


class DemoAToDemoBMappingRepository(BaseAppRepository[DemoAToDemoBMappingModel]):
    """Demo repository."""
    def __init__(self, db):
        super().__init__(db=db, model=DemoAToDemoBMappingModel)
        

    async def insert(self, demo_a_to_demo_b_mapping_data: Dict[str, Any], user_id: UUID = None, workspace_id: UUID = None) -> DemoAToDemoBMappingModel:
        """Insert a new demo (async). user_id optional."""
        try:
            demo_a_to_demo_b_mapping = DemoAToDemoBMappingModel(**demo_a_to_demo_b_mapping_data)
            if user_id is not None:
                demo_a_to_demo_b_mapping.created_by = user_id
            if workspace_id is not None:
                demo_a_to_demo_b_mapping.workspace_id = workspace_id

            self.db.add(demo_a_to_demo_b_mapping)
            await self.db.commit()
            await self.db.refresh(demo_a_to_demo_b_mapping)
            
            return demo_a_to_demo_b_mapping
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_CREATION_ERROR}: {str(e)}") from e

    async def get_by_id(self, demo_a_to_demo_b_mapping_id: UUID, workspace_id: UUID = None) -> DemoAToDemoBMappingModel:
        """Get a demo mapping by ID and workspace (async)."""
        try:
            query = select(self.model).where(
                self.model.demo_a_to_demo_b_mapping_id == demo_a_to_demo_b_mapping_id,
                self.model.workspace_id == workspace_id,
            ).limit(1)
            
            result = await self.db.execute(query)
            demo_a_to_demo_b_mapping = result.scalar_one_or_none()
            
            # Return None if demo is deleted
            if demo_a_to_demo_b_mapping and demo_a_to_demo_b_mapping.status == "deleted":
                raise DemoAToDemoBMappingNotFoundException(demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id)
            
            return demo_a_to_demo_b_mapping
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_RETRIEVAL_ERROR}: {str(e)}") from e


    async def update(self, demo_a_to_demo_b_mapping_id: UUID, demo_a_to_demo_b_mapping_data: Dict[str, Any], user_id: UUID = None, workspace_id: UUID = None) -> DemoAToDemoBMappingModel:
        """Update an existing demo (async)."""
        try:
            demo_a_to_demo_b_mapping = await self.get_by_id(demo_a_to_demo_b_mapping_id, workspace_id=workspace_id)
            if not demo_a_to_demo_b_mapping:
                raise DemoAToDemoBMappingNotFoundException(demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id)
            

            for key, value in demo_a_to_demo_b_mapping_data.items():
                setattr(demo_a_to_demo_b_mapping, key, value)

            if user_id is not None:
                demo_a_to_demo_b_mapping.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a_to_demo_b_mapping)
            
            return demo_a_to_demo_b_mapping
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_UPDATE_ERROR}: {str(e)}") from e


    async def update_status(self, demo_a_to_demo_b_mapping_id: UUID, status: str, error_message: str = None, error_user_message: str = None, user_id: UUID = None, workspace_id: UUID = None) -> DemoAToDemoBMappingModel:
        """Update only the status of a demo (async). Only works if current status is not 'deleted'."""
        try:
            demo_a_to_demo_b_mapping = await self.get_by_id(demo_a_to_demo_b_mapping_id, workspace_id=workspace_id)
            if not demo_a_to_demo_b_mapping:
                raise DemoAToDemoBMappingNotFoundException(demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id)
  
            demo_a_to_demo_b_mapping.status = status
            demo_a_to_demo_b_mapping.error_message = error_message
            demo_a_to_demo_b_mapping.error_user_message = error_user_message
            if user_id is not None:
                demo_a_to_demo_b_mapping.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a_to_demo_b_mapping)
            return demo_a_to_demo_b_mapping
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_STATUS_UPDATE_ERROR}: {str(e)}") from e


    async def update_is_active(self, demo_a_to_demo_b_mapping_id: UUID, is_active: bool, user_id: UUID = None, workspace_id: UUID = None) -> DemoAToDemoBMappingModel:
        """Update only the is_active flag of a demo (async)."""
        try:
            demo_a_to_demo_b_mapping = await self.get_by_id(demo_a_to_demo_b_mapping_id, workspace_id=workspace_id)
            if not demo_a_to_demo_b_mapping:
                raise DemoAToDemoBMappingNotFoundException(demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id)

            demo_a_to_demo_b_mapping.is_active = is_active
            if user_id is not None:
                demo_a_to_demo_b_mapping.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a_to_demo_b_mapping)
            return demo_a_to_demo_b_mapping
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_ACTIVE_UPDATE_ERROR}: {str(e)}") from e

    async def delete(self, demo_a_to_demo_b_mapping_id: UUID, user_id: UUID = None, workspace_id: UUID = None) -> bool:
        """Soft delete a demo (update status & is_active) (async)."""
        try:
            demo_a_to_demo_b_mapping = await self.get_by_id(demo_a_to_demo_b_mapping_id, workspace_id=workspace_id)
            if not demo_a_to_demo_b_mapping:
                raise DemoAToDemoBMappingNotFoundException(demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id)

            # mark as deleted (soft delete) 
            demo_a_to_demo_b_mapping.deleted_at = datetime.now(timezone.utc)
            demo_a_to_demo_b_mapping.deleted_by = user_id
            demo_a_to_demo_b_mapping.status = "deleted"
            demo_a_to_demo_b_mapping.is_active = False
            if user_id is not None:
                demo_a_to_demo_b_mapping.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(demo_a_to_demo_b_mapping)
            
            return True
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETION_ERROR}: {str(e)}") from e

    async def get_all(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get all demos with dynamic filters + direct search + ordering + pagination.
        Uses the base repository's get_all method.
        """
        
        return await super().get_all(
            filters=filters,
            search=search,
            order_by=order_by,
            skip=skip,
            limit=limit,
            user_id=user_id,
            workspace_id=workspace_id
        )

    async def get_by_demo_a_id(
        self,
        demo_a_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get all mappings for a specific demo_a_id (async)."""
        try:
            # Use base repository get_all with filters
            filters = [{"field": "demo_a_id", "operator": "eq", "value": str(demo_a_id)}]
            return await self.get_all(
                filters=filters,
                skip=skip,
                limit=limit,
                workspace_id=workspace_id
            )
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_demo_b_id(
        self,
        demo_b_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get all mappings for a specific demo_b_id (async)."""
        try:
            # Use base repository get_all with filters
            filters = [{"field": "demo_b_id", "operator": "eq", "value": str(demo_b_id)}]
            return await self.get_all(
                filters=filters,
                skip=skip,
                limit=limit,
                workspace_id=workspace_id
            )
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def delete_by_demo_a_id(
        self,
        demo_a_id: UUID,
        user_id: UUID = None,
        workspace_id: UUID = None
    ) -> int:
        """Soft delete all mappings for a specific demo_a_id (async). Returns count of deleted mappings."""
        try:
            # Find all mappings for this demo_a_id
            stmt = select(self.model).where(
                self.model.demo_a_id == demo_a_id,
                self.model.workspace_id == workspace_id,
                self.model.status != "deleted"
            )
            result = await self.db.execute(stmt)
            mappings = result.scalars().all()

            if not mappings:
                raise DemoAToDemoBMappingNotFoundException(
                    message=f"No mappings found for demo_a_id: {demo_a_id}"
                )

            # Mark all as deleted (soft delete)
            deleted_count = 0
            for mapping in mappings:
                mapping.deleted_at = datetime.now(timezone.utc)
                mapping.deleted_by = user_id
                mapping.status = "deleted"
                mapping.is_active = False
                if user_id is not None:
                    mapping.updated_by = user_id
                deleted_count += 1

            # Persist changes
            await self.db.commit()
            
            return deleted_count
        except DemoAToDemoBMappingNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETION_ERROR}: {str(e)}"
            ) from e

    async def delete_by_demo_b_id(
        self,
        demo_b_id: UUID,
        user_id: UUID = None,
        workspace_id: UUID = None
    ) -> int:
        """Soft delete all mappings for a specific demo_b_id (async). Returns count of deleted mappings."""
        try:
            # Find all mappings for this demo_b_id
            stmt = select(self.model).where(
                self.model.demo_b_id == demo_b_id,
                self.model.workspace_id == workspace_id,
                self.model.status != "deleted"
            )
            result = await self.db.execute(stmt)
            mappings = result.scalars().all()

            if not mappings:
                raise DemoAToDemoBMappingNotFoundException(
                    message=f"No mappings found for demo_b_id: {demo_b_id}"
                )

            # Mark all as deleted (soft delete)
            deleted_count = 0
            for mapping in mappings:
                mapping.deleted_at = datetime.now(timezone.utc)
                mapping.deleted_by = user_id
                mapping.status = "deleted"
                mapping.is_active = False
                if user_id is not None:
                    mapping.updated_by = user_id
                deleted_count += 1

            # Persist changes
            await self.db.commit()
            
            return deleted_count
        except DemoAToDemoBMappingNotFoundException:
            raise
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETION_ERROR}: {str(e)}"
            ) from e
