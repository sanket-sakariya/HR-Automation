from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import log_user_activity, log_central
from app.config.constants import LogMessages
from app.schema.demo_a_response_schema import (
    DemoAResponseCreateSchema,
    DemoAResponseUpdateSchema,
    DemoAResponseReadSchema,
    DemoAResponseIsActiveUpdateSchema,
    DemoAResponseStatusUpdateSchema,
)
from app.exception.demo_a_response_exception import (
    DemoAResponseNotFoundException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_a_response_repository import DemoAResponseRepository


class DemoAResponseService(BaseAppService):
    """Demo A Response service."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_a_response_repo = DemoAResponseRepository(db=db)

    async def create(
        self, payload: DemoAResponseCreateSchema, user_id: UUID, workspace_id: UUID
    ) -> DemoAResponseReadSchema:
        """Create a new demo A response."""

        demo_a_response_data = payload.model_dump()

        demo_a_response = await self.demo_a_response_repo.insert(
            demo_a_response_data=demo_a_response_data,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        log_user_activity(
            f"{LogMessages.DEMO_A_RESPONSE_CREATED}: {demo_a_response.name}",
            action_type="demo_a_response_create",
            level="info",
        )

        # Set initial status
        demo_a_response.status = "created"

        return DemoAResponseReadSchema.model_validate(demo_a_response)

    async def read(
        self, demo_a_response_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> DemoAResponseReadSchema:
        """Read a demo A response."""
        demo_a_response = await self.demo_a_response_repo.get_by_id(
            demo_a_response_id=demo_a_response_id, workspace_id=workspace_id
        )
        if not demo_a_response:
            raise DemoAResponseNotFoundException(demo_a_response_id=demo_a_response_id)
        return DemoAResponseReadSchema.model_validate(demo_a_response)

    async def get_by_demo_a_id(
        self, demo_a_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> List[DemoAResponseReadSchema]:
        """Get all responses for a specific demo_a_id."""
        demo_a_responses = await self.demo_a_response_repo.get_by_demo_a_id(
            demo_a_id=demo_a_id, workspace_id=workspace_id
        )
        return [
            DemoAResponseReadSchema.model_validate(resp) for resp in demo_a_responses
        ]

    async def list_all(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """List all demo A responses."""

        result = await self.demo_a_response_repo.get_all(
            filters=filters,
            search=search,
            order_by=order_by,
            skip=skip,
            limit=limit,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        # Convert data to schema objects while preserving pagination structure
        if isinstance(result, dict):
            data = result.get("data", [])
            pagination = result.get("pagination", {})
            schema_data = [
                DemoAResponseReadSchema.model_validate(demo_a_response_item)
                for demo_a_response_item in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            DemoAResponseReadSchema.model_validate(demo_a_response_item)
            for demo_a_response_item in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def update(
        self,
        demo_a_response_id: UUID,
        payload: DemoAResponseUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAResponseReadSchema:
        """Update a demo A response."""
        existing_demo_a_response = await self.demo_a_response_repo.get_by_id(
            demo_a_response_id=demo_a_response_id, workspace_id=workspace_id
        )
        if not existing_demo_a_response:
            raise DemoAResponseNotFoundException(demo_a_response_id=demo_a_response_id)

        payload_dict = payload.model_dump(exclude_unset=True)

        payload_dict["status"] = "updated"
        demo_a_response = await self.demo_a_response_repo.update(
            demo_a_response_id=demo_a_response_id,
            demo_a_response_data=payload_dict,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        log_user_activity(
            f"{LogMessages.DEMO_A_RESPONSE_UPDATED}: {demo_a_response.name}",
            action_type="demo_a_response_update",
        )
        return DemoAResponseReadSchema.model_validate(demo_a_response)

    async def delete(
        self, demo_a_response_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> None:
        """Delete a demo A response."""
        deleted = await self.demo_a_response_repo.delete(
            demo_a_response_id=demo_a_response_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        if not deleted:
            raise DemoAResponseNotFoundException(demo_a_response_id=demo_a_response_id)

        log_user_activity(
            f"{LogMessages.DEMO_A_RESPONSE_DELETED} {demo_a_response_id}",
            action_type="demo_a_response_delete",
        )

    async def update_status(
        self,
        demo_a_response_id: UUID,
        payload: DemoAResponseStatusUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAResponseReadSchema:
        """
        Update demo A response status and error messages.
        """
        log_central(
            message=f"{LogMessages.DEMO_A_RESPONSE_STATUS_UPDATED} {demo_a_response_id} status to {payload.status}",
            level="info",
        )

        # Update status via repository
        demo_a_response = await self.demo_a_response_repo.update_status(
            demo_a_response_id=demo_a_response_id,
            status=payload.status,
            error_message=payload.error_message,
            error_user_message=payload.error_user_message,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return DemoAResponseReadSchema.model_validate(demo_a_response)

    async def update_is_active(
        self,
        demo_a_response_id: UUID,
        payload: DemoAResponseIsActiveUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAResponseReadSchema:
        """
        Update demo A response is_active status.

        Args:
            demo_a_response_id: UUID of the demo A response to update
            payload: Is active update data
            user_id: ID of the user making the update
            workspace_id: ID of the workspace

        Returns:
            Updated demo A response data

        Raises:
            DemoAResponseNotFoundException: If demo A response is not found
            DemoAResponseUpdateException: If update fails
        """
        # Update is_active via repository
        demo_a_response = await self.demo_a_response_repo.update_is_active(
            demo_a_response_id=demo_a_response_id,
            is_active=payload.is_active,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return DemoAResponseReadSchema.model_validate(demo_a_response)
