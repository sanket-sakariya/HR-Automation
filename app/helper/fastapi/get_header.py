from __future__ import annotations
import json
from uuid import UUID
from typing import Annotated, Optional
from fastapi import Header, HTTPException, status

from app.schema.response_schema import ListParamsSchema

def get_user_id(user_id: Annotated[str, Header(alias="user-id", description="The unique identifier for the user.", example="550e8400-e29b-41d4-a716-446655440000")]) -> UUID:
    """Get user ID from 'user-id' header with UUID validation."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user-id header missing")
    
    # Validate UUID format
    try:
        validated_uuid = UUID(user_id)
        return validated_uuid
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid user-id format. Expected UUID, got: '{user_id}'. Example: 550e8400-e29b-41d4-a716-446655440000"
        ) from ValueError

def get_workspace_id(workspace_id: Annotated[str, Header(alias="workspace-id", description="The unique identifier for the workspace.", example="123e4567-e89b-12d3-a456-426614174000")]) -> UUID:
    """Get workspace ID from 'workspace-id' header with UUID validation."""
    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace-id header missing")
    
    # Validate UUID format
    try:
        validated_uuid = UUID(workspace_id)
        return validated_uuid
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid workspace-id format. Expected UUID, got: '{workspace_id}'. Example: 123e4567-e89b-12d3-a456-426614174000"
        ) from ValueError


def get_list_params(
    offset: int = 0,
    limit: int = 100,
    order_by: str = "-created_at",
    search: Optional[str] = None,
    filters: Optional[str] = None,
) -> ListParamsSchema:
    """
    Generalized function to handle list parameters for any API endpoint.
    """
    # Parse filters if provided as a JSON string
    parsed_filters = None
    if filters:
        try:
            # Parse the JSON string completely into actual objects
            data = json.loads(filters)
            # Handle new structure: {"Filters": [...], "logic": "..."}
            if isinstance(data, dict) and "Filters" in data:
                parsed_filters = data # Pass the whole object
            # Handle old structure: a list of filters
            elif isinstance(data, list):
                parsed_filters = {"Filters": data, "logic": "AND"} # Wrap in new structure
            else:
                parsed_filters = None
        except (json.JSONDecodeError, TypeError):
            parsed_filters = None
    
    # Create and return the parameters as an instance of the schema
    return ListParamsSchema(
        offset=offset,
        limit=limit,
        order_by=order_by,
        search=search,
        filters=parsed_filters
    )