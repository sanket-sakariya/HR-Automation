from typing import Final

class DatabaseErrorMessages:
    """Constants for database-related error messages."""
    
    # General database errors
    DATA_RETRIEVAL_ERROR: Final[str] = "Database error during data retrieval"
    
    # DemoA-related database errors
    DEMO_A_CREATION_ERROR: Final[str] = "Database error during demo A creation"
    DEMO_A_RETRIEVAL_ERROR: Final[str] = "Database error while retrieving demo A"
    DEMO_A_UPDATE_ERROR: Final[str] = "Database error during demo A update"
    DEMO_A_STATUS_UPDATE_ERROR: Final[str] = "Database error during demo A status update"
    DEMO_A_ACTIVE_UPDATE_ERROR: Final[str] = "Database error during demo A is_active update"
    DEMO_A_DELETION_ERROR: Final[str] = "Database error during demo A deletion"
    
    # DemoB-related database errors
    DEMO_B_CREATION_ERROR: Final[str] = "Database error during demo B creation"
    DEMO_B_RETRIEVAL_ERROR: Final[str] = "Database error while retrieving demo B"
    DEMO_B_UPDATE_ERROR: Final[str] = "Database error during demo B update"
    DEMO_B_STATUS_UPDATE_ERROR: Final[str] = "Database error during demo B status update"
    DEMO_B_ACTIVE_UPDATE_ERROR: Final[str] = "Database error during demo B is_active update"
    DEMO_B_DELETION_ERROR: Final[str] = "Database error during demo B deletion"
    
    # Mapping-related database errors
    MAPPING_CREATION_ERROR: Final[str] = "Database error during mapping creation"
    MAPPING_RETRIEVAL_ERROR: Final[str] = "Database error while retrieving mapping"
    MAPPING_UPDATE_ERROR: Final[str] = "Database error during mapping update"
    MAPPING_STATUS_UPDATE_ERROR: Final[str] = "Database error during mapping status update"
    MAPPING_ACTIVE_UPDATE_ERROR: Final[str] = "Database error during mapping is_active update"
    MAPPING_DELETION_ERROR: Final[str] = "Database error during mapping deletion"
    
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
    
    # DemoA operations
    DEMO_A_CREATION_FAILED: Final[str] = "Demo A creation failed"
    DEMO_A_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve demo A"
    DEMO_AS_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve demo As"
    DEMO_A_UPDATE_FAILED: Final[str] = "Demo A update failed"
    DEMO_A_DELETION_FAILED: Final[str] = "Failed to delete demo A"
    DEMO_A_STATUS_UPDATE_FAILED: Final[str] = "Failed to update demo A status"
    DEMO_A_ACTIVE_STATUS_UPDATE_FAILED: Final[str] = "Failed to update demo A active status"
    
    # DemoB operations
    DEMO_B_CREATION_FAILED: Final[str] = "Demo B creation failed"
    DEMO_B_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve demo B"
    DEMO_BS_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve demo Bs"
    DEMO_B_UPDATE_FAILED: Final[str] = "Demo B update failed"
    DEMO_B_DELETION_FAILED: Final[str] = "Failed to delete demo B"
    DEMO_B_STATUS_UPDATE_FAILED: Final[str] = "Failed to update demo B status"
    DEMO_B_ACTIVE_STATUS_UPDATE_FAILED: Final[str] = "Failed to update demo B active status"
    
    # Mapping operations
    MAPPING_CREATION_FAILED: Final[str] = "Mapping creation failed"
    MAPPING_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve mapping"
    MAPPINGS_RETRIEVAL_FAILED: Final[str] = "Failed to retrieve mappings"
    MAPPING_UPDATE_FAILED: Final[str] = "Mapping update failed"
    MAPPING_DELETION_FAILED: Final[str] = "Failed to delete mapping"
    MAPPING_STATUS_UPDATE_FAILED: Final[str] = "Failed to update mapping status"
    MAPPING_ACTIVE_STATUS_UPDATE_FAILED: Final[str] = "Failed to update mapping active status"



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
    
    # DemoA operations
    DEMO_A_CREATED: Final[str] = "Demo A created successfully"
    DEMO_A_UPDATED: Final[str] = "Demo A updated successfully"
    DEMO_A_DELETED: Final[str] = "Demo A deleted successfully"
    DEMO_A_RETRIEVED: Final[str] = "Demo A retrieved successfully"
    DEMO_AS_RETRIEVED: Final[str] = "Demo As retrieved successfully"
    DEMO_A_STATUS_UPDATED: Final[str] = "Demo A status updated successfully"
    DEMO_A_ACTIVE_STATUS_UPDATED: Final[str] = "Demo A active status updated successfully"
    
    # DemoB operations
    DEMO_B_CREATED: Final[str] = "Demo B created successfully"
    DEMO_B_UPDATED: Final[str] = "Demo B updated successfully"
    DEMO_B_DELETED: Final[str] = "Demo B deleted successfully"
    DEMO_B_RETRIEVED: Final[str] = "Demo B retrieved successfully"
    DEMO_BS_RETRIEVED: Final[str] = "Demo Bs retrieved successfully"
    DEMO_B_STATUS_UPDATED: Final[str] = "Demo B status updated successfully"
    DEMO_B_ACTIVE_STATUS_UPDATED: Final[str] = "Demo B active status updated successfully"
    
    # Mapping operations
    MAPPING_CREATED: Final[str] = "Mapping created successfully"
    MAPPING_UPDATED: Final[str] = "Mapping updated successfully"
    MAPPING_DELETED: Final[str] = "Mapping deleted successfully"
    MAPPING_RETRIEVED: Final[str] = "Mapping retrieved successfully"
    MAPPINGS_RETRIEVED: Final[str] = "Mappings retrieved successfully"
    MAPPING_STATUS_UPDATED: Final[str] = "Mapping status updated successfully"
    MAPPING_ACTIVE_STATUS_UPDATED: Final[str] = "Mapping active status updated successfully"


class SchemaDescriptions:
    """Constants for schema field descriptions."""
    
    # Demo schema descriptions
    DEMO_STATUS_DESCRIPTION: Final[str] = "Demo status"