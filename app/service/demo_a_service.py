from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import  log_user_activity, log_central
from app.config.constants import  LogMessages
from app.schema.demo_a_schema import (
    DemoACreateSchema, 
    DemoAUpdateSchema, 
    DemoAReadSchema,
    DemoAIsActiveUpdateSchema,
    DemoAStatusUpdateSchema
)
from app.exception.demo_a_exception import (
    DemoANotFoundException,

)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_a_repository import DemoARepository


class DemoAService(BaseAppService):
    """Demo service."""
    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_repo = DemoARepository(db=db)

    async def create(self, payload: DemoACreateSchema, user_id: UUID, workspace_id: UUID) -> DemoAReadSchema:        
        """Create a new demo."""
        
        demo_a_data = payload.model_dump()

        # Convert AnyHttpUrl to string
        if demo_a_data.get("website"):
            demo_a_data["website"] = str(demo_a_data["website"])
        
        if demo_a_data.get("social_accounts"):
            for account in demo_a_data["social_accounts"]:
                if account.get("url"):
                    account["url"] = str(account["url"])

        demo_a = await self.demo_repo.insert(demo_a_data=demo_a_data, user_id=user_id, workspace_id=workspace_id)
        log_user_activity(f"{LogMessages.DEMO_CREATED}: {demo_a.name}", action_type="demo_create", level="info")
        
        # Set initial status
        demo_a.status = "created"
        
        return DemoAReadSchema.model_validate(demo_a)

    async def read(self, demo_a_id: UUID, user_id: UUID, workspace_id: UUID) -> DemoAReadSchema:  
        """Read a demo."""
        demo_a = await self.demo_repo.get_by_id(demo_a_id=demo_a_id, workspace_id=workspace_id)
        if not demo_a:
            raise DemoANotFoundException(demo_a_id=demo_a_id)
        return DemoAReadSchema.model_validate(demo_a)
    
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
            schema_data = [DemoAReadSchema.model_validate(ws) for ws in data]
            return {"data": schema_data, "pagination": pagination}

        # Fallback for non-dict results
        schema_data = [DemoAReadSchema.model_validate(ws) for ws in result]
        return {"data": schema_data, "pagination": {}}

    
    async def update(self, demo_a_id: UUID, payload: DemoAUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAReadSchema:
        """Update a demo."""
        existing_demo_a = await self.demo_repo.get_by_id(demo_a_id=demo_a_id, workspace_id=workspace_id)
        if not existing_demo_a:
            raise DemoANotFoundException(demo_a_id=demo_a_id)
        
        payload_dict = payload.model_dump(exclude_unset=True)
        
        # Convert AnyHttpUrl to string before updating
        if payload_dict.get("website"):
            payload_dict["website"] = str(payload_dict["website"])
        
        if payload_dict.get("social_accounts"):
            for account in payload_dict["social_accounts"]:
                if account.get("url"):
                    account["url"] = str(account["url"])
        
        payload_dict["status"] = "updated"
        demo_a = await self.demo_repo.update(demo_a_id=demo_a_id, demo_a_data=payload_dict, user_id=user_id, workspace_id=workspace_id)

        log_user_activity(f"{LogMessages.DEMO_UPDATED}: {demo_a.name}", action_type="demo_update")
        return DemoAReadSchema.model_validate(demo_a)

    async def delete(self, demo_a_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
        """Delete a demo."""
        deleted = await self.demo_repo.delete(demo_a_id=demo_a_id, user_id=user_id, workspace_id=workspace_id)
        
        if not deleted:
            raise DemoANotFoundException(demo_a_id=demo_a_id)
        
        log_user_activity(f"{LogMessages.DEMO_DELETED} {demo_a_id}", action_type="demo_delete")

    
    async def update_status(self, demo_a_id: UUID, payload: DemoAStatusUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAReadSchema:
        """
        Update demo status and error messages.
        """
        log_central(message=f"{LogMessages.DEMO_STATUS_UPDATED} {demo_a_id} status to {payload.status}", level="info")
        
        # Update status via repository
        demo_a = await self.demo_repo.update_status(
            demo_a_id=demo_a_id, 
            status=payload.status, 
            error_message=payload.error_message,
            error_user_message=payload.error_user_message,
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoAReadSchema.model_validate(demo_a)

    async def update_is_active(self, demo_a_id: UUID, payload: DemoAIsActiveUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoAReadSchema:
        """
        Update demo is_active status.
        
        Args:
            demo_a_id: UUID of the demo to update
            payload: Is active update data
            user_id: ID of the user making the update
            
        Returns:
            Updated demo data
            
        Raises:
            DemoANotFoundException: If demo is not found
            DemoAUpdateException: If update fails
        """
        # Update is_active via repository
        demo_a = await self.demo_repo.update_is_active(
            demo_a_id=demo_a_id, 
            is_active=payload.is_active, 
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoAReadSchema.model_validate(demo_a)