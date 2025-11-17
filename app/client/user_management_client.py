from __future__ import annotations

from typing import Optional, Dict, Any
from uuid import UUID
from app.client.baseapp_client import BaseAppHttpClient
from app.config.config import config


class UserManagementClient(BaseAppHttpClient):
    """Client for communicating with User Management Service."""

    def __init__(self):
        super().__init__(
            base_url=config.USER_MANAGEMENT_SERVICE_URL,
            timeout=config.USER_MANAGEMENT_TIMEOUT,
            retries=config.USER_MANAGEMENT_RETRIES,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    async def get_workspace_members(
        self,
        workspace_id: UUID,
        user_id: UUID,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "-created_at",
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch workspace members from User Management Service.

        Args:
            workspace_id: UUID of the workspace
            user_id: ID of the requesting user
            offset: Pagination offset
            limit: Number of items to return
            order_by: Field to order by
            search: Search query for member names/emails

        Returns:
            Dict containing members data and pagination info
        """

        params: dict = {
            "workspace_id": str(workspace_id),
            "offset": offset,
            "limit": limit,
            "order_by": order_by,
        }

        if search:
            params["search"] = search

        return await self._make_request(
            method="GET",
            endpoint="/user-workspace-mappings/",
            params=params,
            headers={"X-User-ID": str(user_id), "X-Workspace-ID": str(workspace_id)},
        )
