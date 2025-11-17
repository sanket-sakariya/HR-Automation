from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import log_user_activity, log_central
from app.config.constants import LogMessages
from app.schema.demo_a_to_demo_b_mapping_schema import (
    DemoAToDemoBMappingCreateSchema,
    DemoAToDemoBMappingUpdateSchema,
    DemoAToDemoBMappingReadSchema,
    DemoAToDemoBMappingIsActiveUpdateSchema,
    DemoAToDemoBMappingStatusUpdateSchema,
)
from app.exception.demo_a_to_demo_b_mapping_exception import (
    DemoAToDemoBMappingNotFoundException,
)
from app.exception.demo_a_exception import DemoANotFoundException
from app.exception.demo_b_exception import DemoBNotFoundException

from app.service.baseapp_service import BaseAppService
from app.repository.demo_a_to_demo_b_mapping_repository import (
    DemoAToDemoBMappingRepository,
)
from app.repository.demo_a_repository import DemoARepository
from app.repository.demo_b_repository import DemoBRepository


class DemoAToDemoBMappingService(BaseAppService):
    """Mapping service between DemoA and DemoB."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_a_to_demo_b_mapping_repo = DemoAToDemoBMappingRepository(db=db)
        self.demo_a_repo = DemoARepository(db=db)
        self.demo_b_repo = DemoBRepository(db=db)

    async def create(
        self,
        payload: DemoAToDemoBMappingCreateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAToDemoBMappingReadSchema:
        """Create a new mapping."""

        # Check if demo_a exists
        demo_a = await self.demo_a_repo.get_by_id(
            demo_a_id=payload.demo_a_id, workspace_id=workspace_id
        )
        if not demo_a:
            raise DemoANotFoundException(demo_a_id=payload.demo_a_id)

        # Check if demo_b exists
        demo_b = await self.demo_b_repo.get_by_id(
            demo_b_id=payload.demo_b_id, workspace_id=workspace_id
        )
        if not demo_b:
            raise DemoBNotFoundException(demo_b_id=payload.demo_b_id)

        demo_a_to_demo_b_mapping_data = payload.model_dump()
        demo_a_to_demo_b_mapping = await self.demo_a_to_demo_b_mapping_repo.insert(
            demo_a_to_demo_b_mapping_data=demo_a_to_demo_b_mapping_data,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        log_user_activity(
            f"{LogMessages.DEMO_A_TO_DEMO_B_MAPPING_CREATED}: "
            f"{demo_a_to_demo_b_mapping.demo_a_to_demo_b_mapping_id}",
            action_type="mapping_create",
            level="info",
        )

        # Set initial status
        demo_a_to_demo_b_mapping.status = "created"

        return DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping)

    async def read(
        self, demo_a_to_demo_b_mapping_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> DemoAToDemoBMappingReadSchema:
        """Read a mapping."""
        demo_a_to_demo_b_mapping = await self.demo_a_to_demo_b_mapping_repo.get_by_id(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            workspace_id=workspace_id,
        )
        if not demo_a_to_demo_b_mapping:
            raise DemoAToDemoBMappingNotFoundException(
                demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id
            )
        return DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping)

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
        """List all mappings."""

        result = await self.demo_a_to_demo_b_mapping_repo.get_all(
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
                DemoAToDemoBMappingReadSchema.model_validate(
                    demo_a_to_demo_b_mapping_item
                )
                for demo_a_to_demo_b_mapping_item in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping_item)
            for demo_a_to_demo_b_mapping_item in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def update(
        self,
        demo_a_to_demo_b_mapping_id: UUID,
        payload: DemoAToDemoBMappingUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAToDemoBMappingReadSchema:
        """Update a mapping."""
        existing_demo_a_to_demo_b_mapping = await (
            self.demo_a_to_demo_b_mapping_repo.get_by_id(
                demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
                workspace_id=workspace_id,
            )
        )
        if not existing_demo_a_to_demo_b_mapping:
            raise DemoAToDemoBMappingNotFoundException(
                demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id
            )

        # Check if demo_a exists when updating demo_a_id
        if payload.demo_a_id:
            demo_a = await self.demo_a_repo.get_by_id(
                demo_a_id=payload.demo_a_id, workspace_id=workspace_id
            )
            if not demo_a:
                raise DemoANotFoundException(demo_a_id=payload.demo_a_id)

        # Check if demo_b exists when updating demo_b_id
        if payload.demo_b_id:
            demo_b = await self.demo_b_repo.get_by_id(
                demo_b_id=payload.demo_b_id, workspace_id=workspace_id
            )
            if not demo_b:
                raise DemoBNotFoundException(demo_b_id=payload.demo_b_id)

        payload_dict = payload.model_dump(exclude_unset=True)
        payload_dict["status"] = "updated"
        demo_a_to_demo_b_mapping = await self.demo_a_to_demo_b_mapping_repo.update(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            demo_a_to_demo_b_mapping_data=payload_dict,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        log_user_activity(
            f"{LogMessages.DEMO_A_TO_DEMO_B_MAPPING_UPDATED}: "
            f"{demo_a_to_demo_b_mapping.demo_a_to_demo_b_mapping_id}",
            action_type="mapping_update",
        )
        return DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping)

    async def delete(
        self, demo_a_to_demo_b_mapping_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> None:
        """Delete a mapping."""
        deleted = await self.demo_a_to_demo_b_mapping_repo.delete(
            demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )

        if not deleted:
            raise DemoAToDemoBMappingNotFoundException(
                demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id
            )

        log_user_activity(
            f"{LogMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETED} {demo_a_to_demo_b_mapping_id}",
            action_type="mapping_delete",
        )

    async def update_status(
        self,
        demo_a_to_demo_b_mapping_id: UUID,
        payload: DemoAToDemoBMappingStatusUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAToDemoBMappingReadSchema:
        """Update mapping status and error messages."""
        log_central(
            message=(
                f"{LogMessages.DEMO_A_TO_DEMO_B_MAPPING_STATUS_UPDATED} "
                f"{demo_a_to_demo_b_mapping_id} status to {payload.status}"
            ),
            level="info",
        )

        # Update status via repository
        demo_a_to_demo_b_mapping = (
            await self.demo_a_to_demo_b_mapping_repo.update_status(
                demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
                status=payload.status,
                error_message=payload.error_message,
                error_user_message=payload.error_user_message,
                user_id=user_id,
                workspace_id=workspace_id,
            )
        )

        return DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping)

    async def update_is_active(
        self,
        demo_a_to_demo_b_mapping_id: UUID,
        payload: DemoAToDemoBMappingIsActiveUpdateSchema,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DemoAToDemoBMappingReadSchema:
        """Update mapping is_active status."""
        # Update is_active via repository
        demo_a_to_demo_b_mapping = (
            await self.demo_a_to_demo_b_mapping_repo.update_is_active(
                demo_a_to_demo_b_mapping_id=demo_a_to_demo_b_mapping_id,
                is_active=payload.is_active,
                user_id=user_id,
                workspace_id=workspace_id,
            )
        )

        return DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping)

    async def get_by_demo_a_id(
        self,
        demo_a_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get all mappings by demo_a_id."""
        # Verify demo_a exists
        demo_a = await self.demo_a_repo.get_by_id(
            demo_a_id=demo_a_id, workspace_id=workspace_id
        )
        if not demo_a:
            raise DemoANotFoundException(demo_a_id=demo_a_id)

        result = await self.demo_a_to_demo_b_mapping_repo.get_by_demo_a_id(
            demo_a_id=demo_a_id, workspace_id=workspace_id, skip=skip, limit=limit
        )

        # Convert data to schema objects while preserving pagination structure
        if isinstance(result, dict):
            data = result.get("data", [])
            pagination = result.get("pagination", {})
            schema_data = [
                DemoAToDemoBMappingReadSchema.model_validate(
                    demo_a_to_demo_b_mapping_item
                )
                for demo_a_to_demo_b_mapping_item in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping_item)
            for demo_a_to_demo_b_mapping_item in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def get_by_demo_b_id(
        self,
        demo_b_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get all mappings by demo_b_id."""
        # Verify demo_b exists
        demo_b = await self.demo_b_repo.get_by_id(
            demo_b_id=demo_b_id, workspace_id=workspace_id
        )
        if not demo_b:
            raise DemoBNotFoundException(demo_b_id=demo_b_id)

        result = await self.demo_a_to_demo_b_mapping_repo.get_by_demo_b_id(
            demo_b_id=demo_b_id, workspace_id=workspace_id, skip=skip, limit=limit
        )

        # Convert data to schema objects while preserving pagination structure
        if isinstance(result, dict):
            data = result.get("data", [])
            pagination = result.get("pagination", {})
            schema_data = [
                DemoAToDemoBMappingReadSchema.model_validate(
                    demo_a_to_demo_b_mapping_item
                )
                for demo_a_to_demo_b_mapping_item in data
            ]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [
            DemoAToDemoBMappingReadSchema.model_validate(demo_a_to_demo_b_mapping_item)
            for demo_a_to_demo_b_mapping_item in result
        ]
        return {"data": schema_data, "pagination": {}}

    async def delete_by_demo_a_id(
        self, demo_a_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> int:
        """Delete all mappings by demo_a_id. Returns count of deleted mappings."""
        # Verify demo_a exists
        demo_a = await self.demo_a_repo.get_by_id(
            demo_a_id=demo_a_id, workspace_id=workspace_id
        )
        if not demo_a:
            raise DemoANotFoundException(demo_a_id=demo_a_id)

        deleted_count = await self.demo_a_to_demo_b_mapping_repo.delete_by_demo_a_id(
            demo_a_id=demo_a_id, user_id=user_id, workspace_id=workspace_id
        )

        log_user_activity(
            f"{LogMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETED} {deleted_count} "
            f"mapping(s) for demo_a_id {demo_a_id}",
            action_type="mapping_delete",
        )

        return deleted_count

    async def delete_by_demo_b_id(
        self, demo_b_id: UUID, user_id: UUID, workspace_id: UUID
    ) -> int:
        """Delete all mappings by demo_b_id. Returns count of deleted mappings."""
        # Verify demo_b exists
        demo_b = await self.demo_b_repo.get_by_id(
            demo_b_id=demo_b_id, workspace_id=workspace_id
        )
        if not demo_b:
            raise DemoBNotFoundException(demo_b_id=demo_b_id)

        deleted_count = await self.demo_a_to_demo_b_mapping_repo.delete_by_demo_b_id(
            demo_b_id=demo_b_id, user_id=user_id, workspace_id=workspace_id
        )

        log_user_activity(
            f"{LogMessages.DEMO_A_TO_DEMO_B_MAPPING_DELETED} {deleted_count} "
            f"mapping(s) for demo_b_id {demo_b_id}",
            action_type="mapping_delete",
        )

        return deleted_count
