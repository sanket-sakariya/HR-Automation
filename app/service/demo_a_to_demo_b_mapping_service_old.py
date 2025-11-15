from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import  log_user_activity, log_central
from app.config.constants import  LogMessages
from app.schema.demo_a_to_demo_b_mapping_schema import (
    DemoAToDemoBDemoAToDemoBMappingCreateSchema, 
    DemoAToDemoBDemoAToDemoBMappingUpdateSchema, 
    DemoAToDemoBDemoAToDemoBMappingReadSchema,
    DemoAToDemoBDemoAToDemoBMappingIsActiveUpdateSchema,
    DemoAToDemoBDemoAToDemoBMappingStatusUpdateSchema
)
from app.exception.demo_a_to_demo_b_mapping_exception import (
    DemoNotFoundException,

)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_a_to_demo_b_mapping_repository import DemoAToDemoBMappingRepository


class DemoAToDemoBMappingService(BaseAppService):
    """Demo service."""
    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_repo = DemoAToDemoBMappingRepository(db=db)

    async def create(self, payload: DemoAToDemoBDemoAToDemoBMappingCreateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBDemoAToDemoBMappingReadSchema:        
        """Create a new demo."""
        
        demo_data = payload.model_dump()

        # Convert AnyHttpUrl to string
        if demo_data.get("website"):
            demo_data["website"] = str(demo_data["website"])
        
        if demo_data.get("social_accounts"):
            for account in demo_data["social_accounts"]:
                if account.get("url"):
                    account["url"] = str(account["url"])

        demo = await self.demo_repo.insert(demo_data=demo_data, user_id=user_id, workspace_id=workspace_id)
        log_user_activity(f"{LogMessages.DEMO_CREATED}: {demo.name}", action_type="demo_create", level="info")
        
        # Set initial status
        demo.status = "created"
        
        return DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(demo)

    async def read(self, mapping_id: UUID, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBDemoAToDemoBMappingReadSchema:  
        """Read a demo."""
        demo = await self.demo_repo.get_by_id(mapping_id=mapping_id, workspace_id=workspace_id)
        if not demo:
            raise DemoNotFoundException(mapping_id=mapping_id)
        return DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(demo)
    
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
        """List all demos."""
        
        result = await self.demo_repo.get_all(
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
            schema_data = [DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(ws) for ws in data]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(ws) for ws in result]
        return {"data": schema_data, "pagination": {}}

    
    async def update(self, mapping_id: UUID, payload: DemoAToDemoBDemoAToDemoBMappingUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBDemoAToDemoBMappingReadSchema:
        """Update a demo."""
        existing_demo = await self.demo_repo.get_by_id(mapping_id=mapping_id, workspace_id=workspace_id)
        if not existing_demo:
            raise DemoNotFoundException(mapping_id=mapping_id)
        
        payload_dict = payload.model_dump(exclude_unset=True)
        
        # Convert AnyHttpUrl to string before updating
        if payload_dict.get("website"):
            payload_dict["website"] = str(payload_dict["website"])
        
        if payload_dict.get("social_accounts"):
            for account in payload_dict["social_accounts"]:
                if account.get("url"):
                    account["url"] = str(account["url"])
        
        payload_dict["status"] = "updated"
        demo = await self.demo_repo.update(mapping_id=mapping_id, demo_data=payload_dict, user_id=user_id, workspace_id=workspace_id)

        log_user_activity(f"{LogMessages.DEMO_UPDATED}: {demo.name}", action_type="demo_update")
        return DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(demo)

    async def delete(self, mapping_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
        """Delete a demo."""
        deleted = await self.demo_repo.delete(mapping_id=mapping_id, user_id=user_id, workspace_id=workspace_id)
        
        if not deleted:
            raise DemoNotFoundException(mapping_id=mapping_id)
        
        log_user_activity(f"{LogMessages.DEMO_DELETED} {mapping_id}", action_type="demo_delete")

    
    async def update_status(self, mapping_id: UUID, payload: DemoAToDemoBDemoAToDemoBMappingStatusUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBDemoAToDemoBMappingReadSchema:
        """
        Update demo status and error messages.
        """
        log_central(message=f"{LogMessages.DEMO_STATUS_UPDATED} {mapping_id} status to {payload.status}", level="info")
        
        # Update status via repository
        demo = await self.demo_repo.update_status(
            mapping_id=mapping_id, 
            status=payload.status, 
            error_message=payload.error_message,
            error_user_message=payload.error_user_message,
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(demo)

    async def update_is_active(self, mapping_id: UUID, payload: DemoAToDemoBDemoAToDemoBMappingIsActiveUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAToDemoBDemoAToDemoBMappingReadSchema:
        """
        Update demo is_active status.
        
        Args:
            mapping_id: UUID of the demo to update
            payload: Is active update data
            user_id: ID of the user making the update
            
        Returns:
            Updated demo data
            
        Raises:
            DemoNotFoundException: If demo is not found
            DemoUpdateException: If update fails
        """
        # Update is_active via repository
        demo = await self.demo_repo.update_is_active(
            mapping_id=mapping_id, 
            is_active=payload.is_active, 
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoAToDemoBDemoAToDemoBMappingReadSchema.model_validate(demo)