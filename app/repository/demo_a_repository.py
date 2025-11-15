from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.demo_a_model import DemoAModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.demo_exception import (
    DemoNotFoundException
)
from app.exception.baseapp_exception import InternalServerErrorException


class DemoARepository(BaseAppRepository[DemoAModel]):
    """Demo repository."""
    def __init__(self, db):
        super().__init__(db=db, model=DemoAModel)
        

    async def insert(self, demo_data: Dict[str, Any], user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Insert a new demo (async). user_id optional."""
        try:
            demo = DemoAModel(**demo_data)
            if user_id is not None:
                demo.created_by = user_id
            if workspace_id is not None:
                demo.workspace_id = workspace_id

            self.db.add(demo)
            await self.db.commit()
            await self.db.refresh(demo)
            
            return demo
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_CREATION_ERROR}: {str(e)}") from e

    async def get_by_id(self, demo_a_id: UUID, workspace_id: UUID) -> DemoAModel:
        """Get a demo by ID (async)."""
        try:
            stmt = select(self.model).where(self.model.demo_a_id == demo_a_id, self.model.workspace_id == workspace_id)
            result = await self.db.execute(stmt)
            demo = result.scalar_one_or_none()
            # Return None if demo is deleted
            if demo and demo.status == "deleted":
                raise DemoNotFoundException(demo_a_id=demo_a_id)
            return demo
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_RETRIEVAL_ERROR}: {str(e)}") from e


    async def update(self, demo_a_id: UUID, demo_data: Dict[str, Any], user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Update an existing demo (async)."""
        try:
            demo = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo:
                raise DemoNotFoundException(demo_a_id=demo_a_id)
            

            for key, value in demo_data.items():
                setattr(demo, key, value)

            if user_id is not None:
                demo.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo)
            
            return demo
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_UPDATE_ERROR}: {str(e)}") from e


    async def update_status(self, demo_a_id: UUID, status: str, error_message: str = None, error_user_message: str = None, user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Update only the status of a demo (async). Only works if current status is not 'deleted'."""
        try:
            demo = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo:
                raise DemoNotFoundException(demo_a_id=demo_a_id)
  
            demo.status = status
            demo.error_message = error_message
            demo.error_user_message = error_user_message
            if user_id is not None:
                demo.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo)
            return demo
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_STATUS_UPDATE_ERROR}: {str(e)}") from e


    async def update_is_active(self, demo_a_id: UUID, is_active: bool, user_id: UUID = None, workspace_id: UUID = None) -> DemoAModel:
        """Update only the is_active flag of a demo (async)."""
        try:
            demo = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo:
                raise DemoNotFoundException(demo_a_id=demo_a_id)

            demo.is_active = is_active
            if user_id is not None:
                demo.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo)
            return demo
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_ACTIVE_UPDATE_ERROR}: {str(e)}") from e

    async def delete(self, demo_a_id: UUID, user_id: UUID = None, workspace_id: UUID = None) -> bool:
        """Soft delete a demo (update status & is_active) (async)."""
        try:
            demo = await self.get_by_id(demo_a_id, workspace_id=workspace_id)
            if not demo:
                raise DemoNotFoundException(demo_a_id=demo_a_id)

            # mark as deleted (soft delete) 
            demo.deleted_at = datetime.now(timezone.utc)
            demo.deleted_by = user_id
            demo.status = "deleted"
            demo.is_active = False
            if user_id is not None:
                demo.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(demo)
            
            return True
        except SQLAlchemyError as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DEMO_DELETION_ERROR}: {str(e)}") from e

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
