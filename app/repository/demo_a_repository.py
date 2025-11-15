from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.demo_a_model import DemoAModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.demo_a_exception import (
    DemoANotFoundException
)
from app.exception.baseapp_exception import InternalServerErrorException


class DemoARepository(BaseAppRepository[DemoAModel]):
    """Demo repository."""
    def __init__(self, db):
        super().__init__(db=db, model=DemoAModel)
        

    async def insert(self, demo_a_data: Dict[str, Any], user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Insert a new demo (async). user_id optional."""
        try:
            demo_a = DemoAModel(**demo_a_data)
            if user_id is not None:
                demo_a.created_by = user_id
            if workspace_id is not None:
                demo_a.workspace_id = workspace_id

            self.db.add(demo_a)
            await self.db.commit()
            await self.db.refresh(demo_a)
            
            return demo_a
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_CREATION_ERROR}: {str(e)}") from e

    async def get_by_id(self, demo_a_id: UUID, workspace_id: UUID = None) -> DemoAModel:
        """Get a demo by ID and workspace (async)."""
        try:
            query = select(self.model).where(
                self.model.demo_a_id == demo_a_id,
                self.model.workspace_id == workspace_id,
            ).limit(1)
            
            result = await self.db.execute(query)
            demo_a = result.scalar_one_or_none()
            
            # Return None if demo is deleted
            if demo_a and demo_a.status == "deleted":
                raise DemoANotFoundException(demo_a_id=demo_a_id)
            
            return demo_a
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_RETRIEVAL_ERROR}: {str(e)}") from e


    async def update(self, demo_a_id: UUID, demo_a_data: Dict[str, Any], user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Update an existing demo (async)."""
        try:
            demo_a = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo_a:
                raise DemoANotFoundException(demo_a_id=demo_a_id)
            

            for key, value in demo_a_data.items():
                setattr(demo_a, key, value)

            if user_id is not None:
                demo_a.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a)
            
            return demo_a
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_UPDATE_ERROR}: {str(e)}") from e


    async def update_status(self, demo_a_id: UUID, status: str, error_message: str = None, error_user_message: str = None, user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Update only the status of a demo (async). Only works if current status is not 'deleted'."""
        try:
            demo_a = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo_a:
                raise DemoANotFoundException(demo_a_id=demo_a_id)
  
            demo_a.status = status
            demo_a.error_message = error_message
            demo_a.error_user_message = error_user_message
            if user_id is not None:
                demo_a.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a)
            return demo_a
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_STATUS_UPDATE_ERROR}: {str(e)}") from e


    async def update_is_active(self, demo_a_id: UUID, is_active: bool, user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Update only the is_active flag of a demo (async)."""
        try:
            demo_a = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo_a:
                raise DemoANotFoundException(demo_a_id=demo_a_id)

            demo_a.is_active = is_active
            if user_id is not None:
                demo_a.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a)
            return demo_a
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_ACTIVE_UPDATE_ERROR}: {str(e)}") from e

    async def delete(self, demo_a_id: UUID, user_id: UUID = None, workspace_id: UUID = None) -> bool:
        """Soft delete a demo (update status & is_active) (async)."""
        try:
            demo_a = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo_a:
                raise DemoANotFoundException(demo_a_id=demo_a_id)

            # mark as deleted (soft delete) 
            demo_a.deleted_at = datetime.now(timezone.utc)
            demo_a.deleted_by = user_id
            demo_a.status = "deleted"
            demo_a.is_active = False
            if user_id is not None:
                demo_a.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(demo_a)
            
            return True
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_A_DELETION_ERROR}: {str(e)}") from e

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
