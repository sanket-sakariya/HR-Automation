from typing import Final

class DatabaseErrorMessages:
    """Constants for database-related error messages."""
    
    # General database errors
    DATA_RETRIEVAL_ERROR: Final[str] = "Database error during data retrieval"
    
    # Demo-related database errors
    DEMO_CREATION_ERROR: Final[str] = "Database error during demo creation"
    DEMO_RETRIEVAL_ERROR: Final[str] = "Database error while retrieving demo"
    DEMO_UPDATE_ERROR: Final[str] = "Database error during demo update"
    DEMO_STATUS_UPDATE_ERROR: Final[str] = "Database error during demo status update"
    DEMO_ACTIVE_UPDATE_ERROR: Final[str] = "Database error during demo is_active update"
    DEMO_DELETION_ERROR: Final[str] = "Database error during demo deletion"
    
    # User-to-Demo mapping errors
    USER_DEMO_MAPPING_CREATION_ERROR: Final[str] = "Database error during user-demo mapping creation"
    USER_DEMO_MAPPING_RETRIEVAL_ERROR: Final[str] = "Database error while retrieving user-demo mapping"
    USER_DEMO_MAPPING_UPDATE_ERROR: Final[str] = "Database error during user-demo mapping update"
    USER_DEMO_MAPPING_STATUS_UPDATE_ERROR: Final[str] = "Database error during user-demo mapping status update"
    USER_DEMO_MAPPING_ACTIVE_UPDATE_ERROR: Final[str] = "Database error during user-demo mapping is_active update"
    USER_DEMO_MAPPING_DELETION_ERROR: Final[str] = "Database error during user-demo mapping deletion"
    USER_DEMO_MAPPING_COUNT_ERROR: Final[str] = "Database error while counting demo users"



class GeneralErrorMessages:
    """Constants for general error messages."""
    
    # Common operations
    INTERNAL_SERVER_ERROR: Final[str] = "Internal server error"


class ApiErrorMessages:
    """Constants for API endpoint error messages."""
    
    # Demo operations
    DEMO_CREATION_FAILED: Final[str] = "Demo creation failed"
    DEMO_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve demo"
    DEMOS_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve demos"
    DEMO_UPDATE_FAILED: Final[str] = "Demo update failed"
    DEMO_DELETION_FAILED: Final[str] = "Failed to delete demo"
    DEMO_STATUS_UPDATE_FAILED: Final[str] = "Failed to update demo status"
    DEMO_ACTIVE_STATUS_UPDATE_FAILED: Final[str] = "Failed to update demo active status"



class ServiceMessages:
    """Constants for service layer messages."""
    
    # Demo operations
    DEMO_MEMBERS_RETRIEVED: Final[str] = "Demo members retrieved successfully"
    MEMBER_ASSIGNED: Final[str] = "Member assigned to demo successfully"
    MEMBER_REVOKED: Final[str] = "Member revoked from demo successfully"
    
    # Service operations
    FAILED_TO_ASSIGN_MEMBER: Final[str] = "Failed to assign member to demo"



class LogMessages:
    """Constants for log messages."""
    
    # User activities
    DEMO_CREATED: Final[str] = "Created new demo"
    DEMO_UPDATED: Final[str] = "Updated demo"
    DEMO_DELETED: Final[str] = "Deleted demo"
    MEMBER_ASSIGNED: Final[str] = "Assigned member to demo"
    MEMBER_REVOKED: Final[str] = "Revoked member from demo"
    
    # Central logs
    DEMO_STATUS_UPDATED: Final[str] = "Updating demo status"
    
    # Repository logs
    CANNOT_UPDATE_DELETED_DEMO: Final[str] = "Cannot update deleted demo"
    CANNOT_UPDATE_STATUS_DELETED_DEMO: Final[str] = "Cannot update status of deleted demo"
    CANNOT_UPDATE_DELETED_MAPPING: Final[str] = "Cannot update deleted user-to-demo mapping"
    CANNOT_UPDATE_STATUS_DELETED_MAPPING: Final[str] = "Cannot update status of deleted user-to-demo mapping"



class SuccessMessages:
    """Constants for success messages."""
    
    # Demo operations
    DEMO_CREATED: Final[str] = "Demo created successfully"
    DEMO_UPDATED: Final[str] = "Demo updated successfully"
    DEMO_DELETED: Final[str] = "Demo deleted successfully"
    DEMO_RETRIEVED: Final[str] = "Demo retrieved successfully"
    DEMOS_RETRIEVED: Final[str] = "Demos retrieved successfully"
    DEMO_STATUS_UPDATED: Final[str] = "Demo status updated successfully"
    DEMO_ACTIVE_STATUS_UPDATED: Final[str] = "Demo active status updated successfully"


class SchemaDescriptions:
    """Constants for schema field descriptions."""
    
    # Demo schema descriptions
    DEMO_STATUS_DESCRIPTION: Final[str] = "Demo status"