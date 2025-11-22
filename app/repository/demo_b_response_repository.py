from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.demo_b_response_model import DemoBResponseModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.demo_b_response_exception import DemoBResponseNotFoundException
from app.exception.baseapp_exception import InternalServerErrorException


class DemoBResponseRepository(BaseAppRepository[DemoBResponseModel]):
    """Demo B Response repository."""

    def __init__(self, db):
        super().__init__(db=db, model=DemoBResponseModel)

    async def insert(
        self,
        demo_b_response_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoBResponseModel:
        """Insert a new demo B response (async). user_id optional."""
        try:
            demo_b_response = DemoBResponseModel(**demo_b_response_data)
            if user_id is not None:
                demo_b_response.created_by = user_id
            if workspace_id is not None:
                demo_b_response.workspace_id = workspace_id

            self.db.add(demo_b_response)
            await self.db.commit()
            await self.db.refresh(demo_b_response)

            return demo_b_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(self, demo_b_response_id: UUID, workspace_id: UUID = None) -> DemoBResponseModel:
        """Get a demo B response by ID and workspace (async)."""
        try:
            query = (
                select(DemoBResponseModel)
                .where(
                    DemoBResponseModel.demo_b_response_id == demo_b_response_id,
                    DemoBResponseModel.workspace_id == workspace_id,
                )
                .limit(1)
            )

            result = await self.db.execute(query)
            demo_b_response = result.scalar_one_or_none()

            # Return None if demo B response is deleted
            if demo_b_response and demo_b_response.status == "deleted":
                raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

            return demo_b_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_demo_b_id(self, demo_b_id: UUID, workspace_id: UUID = None) -> List[DemoBResponseModel]:
        """Get all demo B responses for a specific demo_b_id (async)."""
        try:
            query = select(DemoBResponseModel).where(
                DemoBResponseModel.demo_b_id == demo_b_id,
                DemoBResponseModel.workspace_id == workspace_id,
                DemoBResponseModel.status != "deleted",
            )

            result = await self.db.execute(query)
            demo_b_responses = result.scalars().all()

            return demo_b_responses
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def update(
        self,
        demo_b_response_id: UUID,
        demo_b_response_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoBResponseModel:
        """Update an existing demo B response (async)."""
        try:
            demo_b_response = await self.get_by_id(demo_b_response_id, workspace_id=workspace_id)
            if not demo_b_response:
                raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

            for key, value in demo_b_response_data.items():
                setattr(demo_b_response, key, value)

            if user_id is not None:
                demo_b_response.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_b_response)

            return demo_b_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_status(
        self,
        demo_b_response_id: UUID,
        status: str,
        error_message: str = None,
        error_user_message: str = None,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoBResponseModel:
        """
        Update only the status of a demo B response (async).
        Only works if current status is not 'deleted'.
        """
        try:
            demo_b_response = await self.get_by_id(demo_b_response_id, workspace_id=workspace_id)
            if not demo_b_response:
                raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

            demo_b_response.status = status
            demo_b_response.error_message = error_message
            demo_b_response.error_user_message = error_user_message
            if user_id is not None:
                demo_b_response.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_b_response)
            return demo_b_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_STATUS_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_is_active(
        self,
        demo_b_response_id: UUID,
        is_active: bool,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoBResponseModel:
        """Update only the is_active flag of a demo B response (async)."""
        try:
            demo_b_response = await self.get_by_id(demo_b_response_id, workspace_id=workspace_id)
            if not demo_b_response:
                raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

            demo_b_response.is_active = is_active
            if user_id is not None:
                demo_b_response.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_b_response)
            return demo_b_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_ACTIVE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def delete(
        self, demo_b_response_id: UUID, user_id: UUID = None, workspace_id: UUID = None
    ) -> bool:
        """Soft delete a demo B response (update status & is_active) (async)."""
        try:
            demo_b_response = await self.get_by_id(demo_b_response_id, workspace_id=workspace_id)
            if not demo_b_response:
                raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

            # mark as deleted (soft delete)
            demo_b_response.deleted_at = datetime.now(timezone.utc)
            demo_b_response.deleted_by = user_id
            demo_b_response.status = "deleted"
            demo_b_response.is_active = False
            if user_id is not None:
                demo_b_response.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(demo_b_response)

            return True
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_B_RESPONSE_DELETION_ERROR}: {str(e)}"
            ) from e

    async def get_all(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get all demo B responses with dynamic filters + direct search + ordering + pagination.
        Uses the base repository's get_all method.
        """

        return await super().get_all(
            filters=filters,
            search=search,
            order_by=order_by,
            skip=skip,
            limit=limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )

