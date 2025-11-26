"""
Example: Using Individual Route Registration with APISIX

This example demonstrates how to register routes individually in APISIX
instead of using the wildcard /* approach.
"""

from app.helper.apisix_helper import get_apisix_helper


async def example_individual_route_registration(app):
    """
    Example showing how to register each FastAPI route individually in APISIX.

    Args:
        app: FastAPI application instance
    """
    apisix_helper = get_apisix_helper()

    # Option 1: Register all routes automatically
    # This will extract all routes from your FastAPI app and register each one
    results = await apisix_helper.register_individual_routes(app)

    # Print results
    for route_path, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {route_path}")

    return results


async def example_with_custom_plugins(app):
    """
    Example showing how to register routes with custom plugins per route.

    Args:
        app: FastAPI application instance
    """
    apisix_helper = get_apisix_helper()

    # Define custom plugins for specific routes
    custom_plugins = {
        "/health": {
            # No authentication needed for health check
            "rbac_abac_workspace": {"disable": True}
        },
        "/api/v1/demo-a": {
            # Add rate limiting for this specific endpoint
            "limit-count": {
                "count": 100,
                "time_window": 60,
                "rejected_code": 429,
                "rejected_msg": "Too many requests",
            }
        },
        "/api/v1/migrations": {
            # Different JWT secret for migrations
            "rbac_abac_workspace": {"jwt_secret": "custom-secret-for-migrations"}
        },
    }

    # Register routes with custom plugins
    results = await apisix_helper.register_individual_routes(
        app, custom_plugins=custom_plugins
    )

    return results


async def example_cleanup(app):
    """
    Example showing how to delete all service routes from APISIX.

    Args:
        app: FastAPI application instance
    """
    apisix_helper = get_apisix_helper()

    # Delete all routes for this service
    success = await apisix_helper.delete_all_service_routes()

    if success:
        print("✅ All service routes deleted from APISIX")
    else:
        print("❌ Failed to delete some routes")

    return success
