from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """ Pagination Schema """
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="Filters to apply")
    search: Optional[str] = Field(None, description="Search query")
    order_by: Optional[str] = Field(None, description="Order by field")
    skip: int = Field(0, description="Number of items to skip")
    limit: int = Field(20, description="Number of items to return")
    user_id: Optional[UUID] = Field(None, description="User ID")
    workspace_id: Optional[UUID] = Field(None, description="Workspace ID")
