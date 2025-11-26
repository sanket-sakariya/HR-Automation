from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config.constants import DatabaseErrorMessages
from app.model.demo_a_response_model import DemoAResponseModel
from app.repository.baseapp_repository import BaseAppRepository

from app.exception.demo_a_response_exception import DemoAResponseNotFoundException
from app.exception.baseapp_exception import InternalServerErrorException


class DemoAResponseRepository(BaseAppRepository[DemoAResponseModel]):
    """Demo A Response repository."""

    def __init__(self, db):
        super().__init__(db=db, model=DemoAResponseModel)

    async def insert(
        self,
        demo_a_response_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoAResponseModel:
        """Insert a new demo A response (async). user_id optional."""
        try:
            demo_a_response = DemoAResponseModel(**demo_a_response_data)
            if user_id is not None:
                demo_a_response.created_by = user_id
            if workspace_id is not None:
                demo_a_response.workspace_id = workspace_id

            self.db.add(demo_a_response)
            await self.db.commit()
            await self.db.refresh(demo_a_response)

            return demo_a_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_CREATION_ERROR}: {str(e)}"
            ) from e

    async def get_by_id(
        self, demo_a_response_id: UUID, workspace_id: UUID = None
    ) -> DemoAResponseModel:
        """Get a demo A response by ID and workspace (async)."""
        try:
            query = (
                select(DemoAResponseModel)
                .where(
                    DemoAResponseModel.demo_a_response_id == demo_a_response_id,
                    DemoAResponseModel.workspace_id == workspace_id,
                )
                .limit(1)
            )

            result = await self.db.execute(query)
            demo_a_response = result.scalar_one_or_none()

            # Return None if demo A response is deleted
            if demo_a_response and demo_a_response.status == "deleted":
                raise DemoAResponseNotFoundException(
                    demo_a_response_id=demo_a_response_id
                )

            return demo_a_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def get_by_demo_a_id(
        self, demo_a_id: UUID, workspace_id: UUID = None
    ) -> List[DemoAResponseModel]:
        """Get all demo A responses for a specific demo_a_id (async)."""
        try:
            query = select(DemoAResponseModel).where(
                DemoAResponseModel.demo_a_id == demo_a_id,
                DemoAResponseModel.workspace_id == workspace_id,
                DemoAResponseModel.status != "deleted",
            )

            result = await self.db.execute(query)
            demo_a_responses = result.scalars().all()

            return demo_a_responses
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_RETRIEVAL_ERROR}: {str(e)}"
            ) from e

    async def update(
        self,
        demo_a_response_id: UUID,
        demo_a_response_data: Dict[str, Any],
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoAResponseModel:
        """Update an existing demo A response (async)."""
        try:
            demo_a_response = await self.get_by_id(
                demo_a_response_id, workspace_id=workspace_id
            )
            if not demo_a_response:
                raise DemoAResponseNotFoundException(
                    demo_a_response_id=demo_a_response_id
                )

            for key, value in demo_a_response_data.items():
                setattr(demo_a_response, key, value)

            if user_id is not None:
                demo_a_response.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a_response)

            return demo_a_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_status(
        self,
        demo_a_response_id: UUID,
        status: str,
        error_message: str = None,
        error_user_message: str = None,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoAResponseModel:
        """
        Update only the status of a demo A response (async).
        Only works if current status is not 'deleted'.
        """
        try:
            demo_a_response = await self.get_by_id(
                demo_a_response_id, workspace_id=workspace_id
            )
            if not demo_a_response:
                raise DemoAResponseNotFoundException(
                    demo_a_response_id=demo_a_response_id
                )

            demo_a_response.status = status
            demo_a_response.error_message = error_message
            demo_a_response.error_user_message = error_user_message
            if user_id is not None:
                demo_a_response.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a_response)
            return demo_a_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_STATUS_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def update_is_active(
        self,
        demo_a_response_id: UUID,
        is_active: bool,
        user_id: UUID = None,
        workspace_id: UUID = None,
    ) -> DemoAResponseModel:
        """Update only the is_active flag of a demo A response (async)."""
        try:
            demo_a_response = await self.get_by_id(
                demo_a_response_id, workspace_id=workspace_id
            )
            if not demo_a_response:
                raise DemoAResponseNotFoundException(
                    demo_a_response_id=demo_a_response_id
                )

            demo_a_response.is_active = is_active
            if user_id is not None:
                demo_a_response.updated_by = user_id

            await self.db.commit()
            await self.db.refresh(demo_a_response)
            return demo_a_response
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_ACTIVE_UPDATE_ERROR}: {str(e)}"
            ) from e

    async def delete(
        self, demo_a_response_id: UUID, user_id: UUID = None, workspace_id: UUID = None
    ) -> bool:
        """Soft delete a demo A response (update status & is_active) (async)."""
        try:
            demo_a_response = await self.get_by_id(
                demo_a_response_id, workspace_id=workspace_id
            )
            if not demo_a_response:
                raise DemoAResponseNotFoundException(
                    demo_a_response_id=demo_a_response_id
                )

            # mark as deleted (soft delete)
            demo_a_response.deleted_at = datetime.now(timezone.utc)
            demo_a_response.deleted_by = user_id
            demo_a_response.status = "deleted"
            demo_a_response.is_active = False
            if user_id is not None:
                demo_a_response.updated_by = user_id

            # persist changes
            await self.db.commit()
            await self.db.refresh(demo_a_response)

            return True
        except SQLAlchemyError as e:
            raise InternalServerErrorException(
                message=f"{DatabaseErrorMessages.DEMO_A_RESPONSE_DELETION_ERROR}: {str(e)}"
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
        Get all demo A responses with dynamic filters + direct search + ordering + pagination.
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
