from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import  log_user_activity, log_central
from app.config.constants import  LogMessages
from app.schema.demo_b_schema import (
    DemoBCreateSchema, 
    DemoBUpdateSchema, 
    DemoBReadSchema,
    DemoBIsActiveUpdateSchema,
    DemoBStatusUpdateSchema
)
from app.exception.demo_b_exception import (
    DemoBNotFoundException,

)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_b_repository import DemoBRepository


class DemoBService(BaseAppService):
    """Demo service."""
    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_repo = DemoBRepository(db=db)

    async def create(self, payload: DemoBCreateSchema, user_id: UUID, workspace_id: UUID) -> DemoBReadSchema:        
        """Create a new demo."""
        
        demo_b_data = payload.model_dump()

        # Convert AnyHttpUrl to string
        if demo_b_data.get("website"):
            demo_b_data["website"] = str(demo_b_data["website"])
        
        if demo_b_data.get("social_accounts"):
            for account in demo_b_data["social_accounts"]:
                if account.get("url"):
                    account["url"] = str(account["url"])

        demo_b = await self.demo_repo.insert(demo_b_data=demo_b_data, user_id=user_id, workspace_id=workspace_id)
        log_user_activity(f"{LogMessages.DEMO_CREATED}: {demo_b.name}", action_type="demo_create", level="info")
        
        # Set initial status
        demo_b.status = "created"
        
        return DemoBReadSchema.model_validate(demo_b)

    async def read(self, demo_b_id: UUID, user_id: UUID, workspace_id: UUID) -> DemoBReadSchema:  
        """Read a demo."""
        demo_b = await self.demo_repo.get_by_id(demo_b_id=demo_b_id, workspace_id=workspace_id)
        if not demo_b:
            raise DemoBNotFoundException(demo_b_id=demo_b_id)
        return DemoBReadSchema.model_validate(demo_b)
    
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
            schema_data = [DemoBReadSchema.model_validate(ws) for ws in data]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [DemoBReadSchema.model_validate(ws) for ws in result]
        return {"data": schema_data, "pagination": {}}

    
    async def update(self, demo_b_id: UUID, payload: DemoBUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoBReadSchema:
        """Update a demo."""
        existing_demo_b = await self.demo_repo.get_by_id(demo_b_id=demo_b_id, workspace_id=workspace_id)
        if not existing_demo_b:
            raise DemoBNotFoundException(demo_b_id=demo_b_id)
        
        payload_dict = payload.model_dump(exclude_unset=True)
        
        # Convert AnyHttpUrl to string before updating
        if payload_dict.get("website"):
            payload_dict["website"] = str(payload_dict["website"])
        
        if payload_dict.get("social_accounts"):
            for account in payload_dict["social_accounts"]:
                if account.get("url"):
                    account["url"] = str(account["url"])
        
        payload_dict["status"] = "updated"
        demo_b = await self.demo_repo.update(demo_b_id=demo_b_id, demo_b_data=payload_dict, user_id=user_id, workspace_id=workspace_id)

        log_user_activity(f"{LogMessages.DEMO_UPDATED}: {demo_b.name}", action_type="demo_update")
        return DemoBReadSchema.model_validate(demo_b)

    async def delete(self, demo_b_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
        """Delete a demo."""
        deleted = await self.demo_repo.delete(demo_b_id=demo_b_id, user_id=user_id, workspace_id=workspace_id)
        
        if not deleted:
            raise DemoBNotFoundException(demo_b_id=demo_b_id)
        
        log_user_activity(f"{LogMessages.DEMO_DELETED} {demo_b_id}", action_type="demo_delete")

    
    async def update_status(self, demo_b_id: UUID, payload: DemoBStatusUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoBReadSchema:
        """
        Update demo status and error messages.
        """
        log_central(message=f"{LogMessages.DEMO_STATUS_UPDATED} {demo_b_id} status to {payload.status}", level="info")
        
        # Update status via repository
        demo_b = await self.demo_repo.update_status(
            demo_b_id=demo_b_id, 
            status=payload.status, 
            error_message=payload.error_message,
            error_user_message=payload.error_user_message,
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoBReadSchema.model_validate(demo_b)

    async def update_is_active(self, demo_b_id: UUID, payload: DemoBIsActiveUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoBReadSchema:
        """
        Update demo is_active status.
        
        Args:
            demo_b_id: UUID of the demo to update
            payload: Is active update data
            user_id: ID of the user making the update
            
        Returns:
            Updated demo data
            
        Raises:
            DemoBNotFoundException: If demo is not found
            DemoBUpdateException: If update fails
        """
        # Update is_active via repository
        demo_b = await self.demo_repo.update_is_active(
            demo_b_id=demo_b_id, 
            is_active=payload.is_active, 
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoBReadSchema.model_validate(demo_b)