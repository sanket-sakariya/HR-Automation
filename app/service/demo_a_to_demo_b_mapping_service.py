from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import log_user_activity, log_central
from app.schema.demo_a_to_demo_b_mapping_schema import (
    DemoAToDemoBMappingCreateSchema,
    DemoAToDemoBMappingUpdateSchema,
    DemoAToDemoBMappingReadSchema,
    DemoAToDemoBMappingIsActiveUpdateSchema,
    DemoAToDemoBMappingStatusUpdateSchema
)
from app.exception.demo_a_to_demo_b_mapping_exception import (
    DemoAToDemoBMappingNotFoundException,
)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_a_to_demo_b_mapping_repository import DemoAToDemoBMappingRepository


class DemoAToDemoBMappingService(BaseAppService):
    """Mapping service between DemoA and DemoB."""
    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.mapping_repo = DemoAToDemoBMappingRepository(db=db)

    async def create(self, payload: DemoAToDemoBMappingCreateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBMappingReadSchema:
        """Create a new mapping."""
        
        demo_a_to_demo_b_mapping_data = payload.model_dump()
        mapping = await self.mapping_repo.insert(demo_a_to_demo_b_mapping_data=demo_a_to_demo_b_mapping_data, user_id=user_id, workspace_id=workspace_id)
        log_user_activity(f"Created mapping: {mapping.mapping_id}", action_type="mapping_create", level="info")
        
        # Set initial status
        mapping.status = "created"
        
        return DemoAToDemoBMappingReadSchema.model_validate(mapping)

    async def read(self, mapping_id: UUID, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBMappingReadSchema:
        """Read a mapping."""
        mapping = await self.mapping_repo.get_by_id(mapping_id=mapping_id, workspace_id=workspace_id)
        if not mapping:
            raise DemoAToDemoBMappingNotFoundException(mapping_id=mapping_id)
        return DemoAToDemoBMappingReadSchema.model_validate(mapping)
    
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
        
        result = await self.mapping_repo.get_all(
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
            schema_data = [DemoAToDemoBMappingReadSchema.model_validate(ws) for ws in data]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [DemoAToDemoBMappingReadSchema.model_validate(ws) for ws in result]
        return {"data": schema_data, "pagination": {}}
    
    async def update(self, mapping_id: UUID, payload: DemoAToDemoBMappingUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBMappingReadSchema:
        """Update a mapping."""
        existing_mapping = await self.mapping_repo.get_by_id(mapping_id=mapping_id, workspace_id=workspace_id)
        if not existing_mapping:
            raise DemoAToDemoBMappingNotFoundException(mapping_id=mapping_id)
        
        payload_dict = payload.model_dump(exclude_unset=True)
        payload_dict["status"] = "updated"
        mapping = await self.mapping_repo.update(mapping_id=mapping_id, demo_a_to_demo_b_mapping_data=payload_dict, user_id=user_id, workspace_id=workspace_id)

        log_user_activity(f"Updated mapping: {mapping.mapping_id}", action_type="mapping_update")
        return DemoAToDemoBMappingReadSchema.model_validate(mapping)

    async def delete(self, mapping_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
        """Delete a mapping."""
        deleted = await self.mapping_repo.delete(mapping_id=mapping_id, user_id=user_id, workspace_id=workspace_id)
        
        if not deleted:
            raise DemoAToDemoBMappingNotFoundException(mapping_id=mapping_id)
        
        log_user_activity(f"Deleted mapping {mapping_id}", action_type="mapping_delete")
    
    async def update_status(self, mapping_id: UUID, payload: DemoAToDemoBMappingStatusUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBMappingReadSchema:
        """Update mapping status and error messages."""
        log_central(message=f"Updating mapping {mapping_id} status to {payload.status}", level="info")
        
        # Update status via repository
        mapping = await self.mapping_repo.update_status(
            mapping_id=mapping_id,
            status=payload.status,
            error_message=payload.error_message,
            error_user_message=payload.error_user_message,
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoAToDemoBMappingReadSchema.model_validate(mapping)

    async def update_is_active(self, mapping_id: UUID, payload: DemoAToDemoBMappingIsActiveUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBMappingReadSchema:
        """Update mapping is_active status."""
        # Update is_active via repository
        mapping = await self.mapping_repo.update_is_active(
            mapping_id=mapping_id,
            is_active=payload.is_active,
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoAToDemoBMappingReadSchema.model_validate(mapping)
