from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import log_user_activity, log_central
from app.config.constants import LogMessages
from app.schema.demo_b_response_schema import (
    DemoBResponseCreateSchema,
    DemoBResponseUpdateSchema,
    DemoBResponseReadSchema,
    DemoBResponseIsActiveUpdateSchema,
    DemoBResponseStatusUpdateSchema,
)
from app.exception.demo_b_response_exception import (
    DemoBResponseNotFoundException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_b_response_repository import DemoBResponseRepository


class DemoBResponseService(BaseAppService):
    """Demo B Response service."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_b_response_repo = DemoBResponseRepository(db=db)

    async def create(
        self, payload: DemoBResponseCreateSchema, user_id: UUID, workspace_id: UUID
    ) -> DemoBResponseReadSchema:
        """Create a new demo B response."""

        demo_b_response_data = payload.model_dump()

        demo_b_response = await self.demo_b_response_repo.insert(
            demo_b_response_data=demo_b_response_data,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        log_user_activity(
            f"{LogMessages.DEMO_B_RESPONSE_CREATED}: {demo_b_response.name}",
            action_type="demo_b_response_create",
            level="info",
        )

        # Set initial status
        demo_b_response.status = "created"

        return DemoBResponseReadSchema.model_validate(demo_b_response)

    async def read(
        self, demo_b_response_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> DemoBResponseReadSchema:
        """Read a demo B response."""
        demo_b_response = await self.demo_b_response_repo.get_by_id(
            demo_b_response_id=demo_b_response_id, workspace_id=workspace_id
        )
        if not demo_b_response:
            raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)
        return DemoBResponseReadSchema.model_validate(demo_b_response)

    async def get_by_demo_b_id(
        self, demo_b_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> List[DemoBResponseReadSchema]:
        """Get all responses for a specific demo_b_id."""
        demo_b_responses = await self.demo_b_response_repo.get_by_demo_b_id(
            demo_b_id=demo_b_id, workspace_id=workspace_id
        )
        return [
            DemoBResponseReadSchema.model_validate(resp) for resp in demo_b_responses
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
        """List all demo B responses."""

        result = await self.demo_b_response_repo.get_all(
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
                DemoBResponseReadSchema.model_validate(demo_b_response_item)
                for demo_b_response_item in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            DemoBResponseReadSchema.model_validate(demo_b_response_item)
            for demo_b_response_item in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def update(
        self,
        demo_b_response_id: UUID,
        payload: DemoBResponseUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoBResponseReadSchema:
        """Update a demo B response."""
        existing_demo_b_response = await self.demo_b_response_repo.get_by_id(
            demo_b_response_id=demo_b_response_id, workspace_id=workspace_id
        )
        if not existing_demo_b_response:
            raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

        payload_dict = payload.model_dump(exclude_unset=True)

        payload_dict["status"] = "updated"
        demo_b_response = await self.demo_b_response_repo.update(
            demo_b_response_id=demo_b_response_id,
            demo_b_response_data=payload_dict,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        log_user_activity(
            f"{LogMessages.DEMO_B_RESPONSE_UPDATED}: {demo_b_response.name}",
            action_type="demo_b_response_update",
        )
        return DemoBResponseReadSchema.model_validate(demo_b_response)

    async def delete(
        self, demo_b_response_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> None:
        """Delete a demo B response."""
        deleted = await self.demo_b_response_repo.delete(
            demo_b_response_id=demo_b_response_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        if not deleted:
            raise DemoBResponseNotFoundException(demo_b_response_id=demo_b_response_id)

        log_user_activity(
            f"{LogMessages.DEMO_B_RESPONSE_DELETED} {demo_b_response_id}",
            action_type="demo_b_response_delete",
        )

    async def update_status(
        self,
        demo_b_response_id: UUID,
        payload: DemoBResponseStatusUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoBResponseReadSchema:
        """
        Update demo B response status and error messages.
        """
        log_central(
            message=f"{LogMessages.DEMO_B_RESPONSE_STATUS_UPDATED} {demo_b_response_id} status to {payload.status}",
            level="info",
        )

        # Update status via repository
        demo_b_response = await self.demo_b_response_repo.update_status(
            demo_b_response_id=demo_b_response_id,
            status=payload.status,
            error_message=payload.error_message,
            error_user_message=payload.error_user_message,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return DemoBResponseReadSchema.model_validate(demo_b_response)

    async def update_is_active(
        self,
        demo_b_response_id: UUID,
        payload: DemoBResponseIsActiveUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoBResponseReadSchema:
        """
        Update demo B response is_active status.

        Args:
            demo_b_response_id: UUID of the demo B response to update
            payload: Is active update data
            user_id: ID of the user making the update
            workspace_id: ID of the workspace

        Returns:
            Updated demo B response data

        Raises:
            DemoBResponseNotFoundException: If demo B response is not found
            DemoBResponseUpdateException: If update fails
        """
        # Update is_active via repository
        demo_b_response = await self.demo_b_response_repo.update_is_active(
            demo_b_response_id=demo_b_response_id,
            is_active=payload.is_active,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        return DemoBResponseReadSchema.model_validate(demo_b_response)
