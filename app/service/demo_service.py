from __future__ import annotations

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import  log_user_activity, log_central
from app.config.constants import  LogMessages
from app.schema.demo_schema import (
    DemoCreateSchema, 
    DemoUpdateSchema, 
    DemoReadSchema,
    DemoStatusUpdateSchema,
    DemoIsActiveUpdateSchema
)
from app.exception.demo_exception import (
    DemoNotFoundException,

)

from app.service.baseapp_service import BaseAppService
from app.repository.demo_repository import DemoRepository
from app.config.config import config

class DemoService(BaseAppService):
    """Demo service."""
    def __init__(self, db: AsyncSession):
        super().__init__(db=db)
        self.demo_repo = DemoRepository(db=db)

    async def create(self, payload: DemoCreateSchema, user_id: UUID, workspace_id: UUID) -> DemoReadSchema:        
        """Create a new demo."""
        demo = await self.demo_repo.insert(demo_data=payload.model_dump(), user_id=user_id, workspace_id=workspace_id)
        log_user_activity(f"{LogMessages.DEMO_CREATED}: {demo.name}", action_type="demo_create", level="info")
        
        # Set initial status
        demo.status = "created"
        
        return DemoReadSchema.model_validate(demo)

    async def read(self, demo_id: UUID, user_id: UUID, workspace_id: UUID) -> DemoReadSchema:
        """Read a demo."""
        demo = await self.demo_repo.get_by_id(demo_id=demo_id, workspace_id=workspace_id)
        if not demo:
            raise DemoNotFoundException(demo_id=demo_id)
        return DemoReadSchema.model_validate(demo)
    
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
            schema_data = [DemoReadSchema.model_validate(ws) for ws in data]
            return {"data": schema_data, "pagination": pagination}
        else:
            # Fallback for non-dict results
            schema_data = [DemoReadSchema.model_validate(ws) for ws in result]
            return {"data": schema_data, "pagination": {}}

    
    async def update(self, demo_id: UUID, payload: DemoUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoReadSchema:
        """Update a demo."""
        existing_demo = await self.demo_repo.get_by_id(demo_id=demo_id, workspace_id=workspace_id)
        if not existing_demo:
            raise DemoNotFoundException(demo_id=demo_id)
        
        payload_dict = payload.model_dump(exclude_unset=True)
        
        payload_dict["status"] = "updated"
        demo = await self.demo_repo.update(demo_id=demo_id, demo_data=payload_dict, user_id=user_id, workspace_id=workspace_id)

        log_user_activity(f"{LogMessages.DEMO_UPDATED}: {demo.name}", action_type="demo_update")
        return DemoReadSchema.model_validate(demo)

    async def delete(self, demo_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
        """Delete a demo."""
        deleted = await self.demo_repo.delete(demo_id=demo_id, user_id=user_id, workspace_id=workspace_id)
        
        if not deleted:
            raise DemoNotFoundException(demo_id=demo_id)
        
        log_user_activity(f"{LogMessages.DEMO_DELETED} {demo_id}", action_type="demo_delete")

    
    async def update_status(self, demo_id: UUID, payload: DemoStatusUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoReadSchema:
        """
        Update demo status and error messages.
        """
        log_central(message=f"{LogMessages.DEMO_STATUS_UPDATED} {demo_id} status to {payload.status}", level="info")
        
        # Update status via repository
        demo = await self.demo_repo.update_status(
            demo_id=demo_id, 
            status=payload.status, 
            user_id=user_id,
            workspace_id=workspace_id
        )

        # Update error messages if provided
        update_data = {}
        if payload.error_message is not None:
            update_data["error_message"] = payload.error_message
        if payload.error_user_message is not None:
            update_data["error_user_message"] = payload.error_user_message

        if update_data:
            demo = await self.demo_repo.update(
                demo_id=demo_id, 
                demo_data=update_data, 
                user_id=user_id,
                workspace_id=workspace_id
            )

        return DemoReadSchema.model_validate(demo)

    async def update_is_active(self, demo_id: UUID, payload: DemoIsActiveUpdateSchema, user_id: UUID, workspace_id: UUID) -> DemoReadSchema:
        """
        Update demo is_active status.
        
        Args:
            demo_id: UUID of the demo to update
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
            demo_id=demo_id, 
            is_active=payload.is_active, 
            user_id=user_id,
            workspace_id=workspace_id
        )

        return DemoReadSchema.model_validate(demo)