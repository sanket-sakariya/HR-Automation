"""APISIX Gateway Helper for route registration.

This module provides utilities to register FastAPI routes with APISIX Gateway.

Two registration modes are supported:

1. **Wildcard Mode** (default):
   - Registers a single route: /{service_name}/*
   - All endpoints share the same plugins and configuration
   - Simpler setup, less granular control

2. **Individual Route Mode** (recommended for production):
   - Registers each FastAPI route separately
   - Each endpoint can have custom plugins, rate limits, authentication
   - More control, better monitoring, enhanced security

Usage:
    # Enable individual route mode in .env.dev:
    # USE_INDIVIDUAL_APISIX_ROUTES=true

    # The system automatically extracts routes from FastAPI app and registers them
    # See app/main.py for implementation

Available methods:
    - extract_routes_from_fastapi(app): Extract all routes from FastAPI app
    - register_individual_routes(app, custom_plugins): Register each route individually
    - register_route(): Register wildcard route (traditional method)
    - delete_all_service_routes(): Delete all service routes from APISIX
    - list_service_routes(): List all registered routes for this service
    - get_route_details(route_id): Get detailed info about a specific route
"""

import asyncio
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute  # pylint: disable=import-error
from app.config.apisix_config import get_apisix_config
from app.config.baseapp_config import get_base_config
from app.config.logger_config import logger


class APISIXHelper:
    """Helper class to manage APISIX Gateway route registration."""

    def __init__(self):
        """Initialize APISIX helper with configuration."""
        self.config = get_apisix_config()
        self.base_config = get_base_config()
        self.admin_url = (
            f"{self.config.APISIX_ADMIN_URL}/apisix/admin/routes/"
            f"{self.config.APISIX_ROUTE_NAME}"
        )
        self.headers = {
            "X-API-KEY": self.config.APISIX_ADMIN_API_KEY,
            "Content-Type": "application/json",
        }

    def _sanitize_route_id(self, route_name: str) -> str:
        """
        Sanitize route name to create a valid APISIX route ID.

        Args:
            route_name: Original route name from FastAPI

        Returns:
            Sanitized route ID safe for APISIX
        """
        # Replace special characters with underscores
        sanitized = (
            route_name.replace("-", "_")
            .replace(":", "_")
            .replace("{", "")
            .replace("}", "")
        )
        # Remove any other non-alphanumeric characters except underscores
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in sanitized)
        # Remove consecutive underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_")

    def _replace_path_params_with_wildcard(self, path: str) -> str:
        """
        Replace path parameters in curly braces with asterisks.

        Args:
            path: Original path with parameters like /api/v1/workspace/{workspace_id}/

        Returns:
            Path with wildcards like /api/v1/workspace/*/

        Example:
            Input:  /workspace-management-service/api/v1/workspace/update/is-active/{workspace_id}/
            Output: /workspace-management-service/api/v1/workspace/update/is-active/*/
        """
        import re
        # Replace any text within curly braces with a single asterisk
        return re.sub(r'\{[^}]+\}', '*', path)

    async def _generate_routes_csv(
        self, route_tasks: List[tuple]
    ) -> None:
        """
        Generate a CSV file containing all registered APISIX routes.

        Args:
            route_tasks: List of tuples containing (route_id, route_config, route_info, route_path)
        """
        try:
            # Determine project root path (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            csv_path = project_root / "apisix.csv"

            # Prepare CSV data
            with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
                fieldnames = ['route_id', 'uri', 'methods', 'status', 'tags', 'is_public']
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write each route
                for route_id, route_config, route_info, _ in route_tasks:
                    # Check if route is public (no RBAC plugin)
                    is_public = "rbac_abac_workspace" not in route_config.get("plugins", {})

                    writer.writerow({
                        'route_id': route_id,
                        'uri': route_config.get('uri', ''),
                        'methods': ','.join(route_config.get('methods', [])),
                        'status': route_config.get('status', 0),
                        'tags': ','.join(route_info.get('tags', [])),
                        'is_public': 'Yes' if is_public else 'No'
                    })

            logger.info(f"✅ Generated APISIX routes CSV file at: {csv_path}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error generating APISIX CSV file: {e}")

    def extract_routes_from_fastapi(self, app: FastAPI) -> List[Dict[str, Any]]:
        """
        Extract all routes from a FastAPI application.

        Args:
            app: FastAPI application instance

        Returns:
            List of dictionaries containing route information
        """
        routes = []

        for route in app.routes:
            if isinstance(route, APIRoute):
                # Extract methods from the route, include all methods (GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD)
                methods = list(route.methods or ["GET"])
                methods.append("OPTIONS")
                methods.append("HEAD")

                if not methods:
                    logger.debug(
                        f"⏭️  Skipping route with no valid methods: {route.path}"
                    )
                    continue

                route_info = {
                    "path": route.path,
                    "methods": methods,
                    "name": route.name,
                    "tags": list(route.tags) if route.tags else [],
                }
                routes.append(route_info)
            else:
                # Handle non-APIRoute routes (like openapi.json, redoc)
                # These are typically Route or Mount objects
                if hasattr(route, "path"):
                    # Include openapi.json and redoc if they exist
                    # Check both with and without service name prefix
                    openapi_paths = [
                        "/openapi.json",
                        f"/{self.base_config.SERVICE_NAME}/openapi.json",
                    ]
                    redoc_paths = ["/redoc", f"/{self.base_config.SERVICE_NAME}/redoc"]

                    if route.path in openapi_paths + redoc_paths:
                        route_info = {
                            "path": route.path,
                            "methods": ["GET"],
                            "name": route.path.replace("/", "_").strip("_"),
                            "tags": [],
                        }
                        routes.append(route_info)

        logger.info(f"📋 Extracted {len(routes)} routes from FastAPI application")
        return routes

    def _is_public_path(self, route_path: str) -> bool:
        """
        Check if a route path is in the public paths list.

        Args:
            route_path: The route path to check (e.g., /demo-management-service/api/v1/health/)

        Returns:
            True if the path is public (no auth required), False otherwise
        """
        # Get public paths from config
        public_paths_str = self.base_config.APISIX_PUBLIC_PATHS
        if not public_paths_str:
            return False

        # Split comma-separated list and strip whitespace
        public_paths = [p.strip() for p in public_paths_str.split(",")]  # pylint: disable=no-member

        # Direct comparison since both route_path and public_paths include service prefix
        return route_path in public_paths

    def _get_default_plugins(self, is_public: bool = False) -> Dict[str, Any]:
        """
        Get default APISIX plugins configuration.

        Args:
            is_public: If True, disables authentication plugins
        """
        plugins = {
            "cors": {
                "allow_origins": (
                    "http://localhost,http://localhost:80,http://localhost:3000,"
                    "http://localhost:8080,http://127.0.0.1,http://127.0.0.1:80,"
                    "http://127.0.0.1:3000,http://127.0.0.1:8080,"
                    "http://articleinnovator.com,http://www.articleinnovator.com,"
                    "https://articleinnovator.com,https://www.articleinnovator.com,"
                    "http://botxbyte.com,http://www.botxbyte.com,"
                    "https://botxbyte.com,https://www.botxbyte.com,"
                    "https://claude.ai,https://www.claudeusercontent.com"
                ),
                "allow_methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD",
                "allow_headers": (
                    "Content-Type,Authorization,X-Correlation-ID,Accept,Origin,"
                    "X-Requested-With,X-API-KEY,Cache-Control,Pragma,Expires,DNT,"
                    "User-Agent,Keep-Alive,If-Modified-Since,X-CustomHeader,"
                    "workspace-id,user-id"
                ),
                "expose_headers": (
                    "Content-Length,Content-Type,X-Correlation-ID,Authorization"
                ),
                "allow_credential": True,
                "max_age": 86400,
            },
        }

        # Only add RBAC plugin for protected routes
        if not is_public:
            plugins["rbac_abac_workspace"] = {
                "jwt_secret": self.config.APISIX_JWT_SECRET
            }

        return plugins

    async def register_individual_routes(  # pylint: disable=too-many-locals
        self, app: FastAPI, custom_plugins: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, bool]:
        """
        Register each FastAPI route individually in APISIX.

        Args:
            app: FastAPI application instance
            custom_plugins: Optional custom plugins per route (keyed by route path)
                Example:
                {
                    "/api/v1/health": {
                        "rbac_abac_workspace": {"disable": True}  # No auth for health
                    },
                    "/api/v1/demo-a": {
                        "limit-count": {  # Rate limiting
                            "count": 100,
                            "time_window": 60,
                            "rejected_code": 429
                        }
                    }
                }

        Returns:
            Dictionary with route paths as keys and registration status as values
        """

        if not self.config.IS_APISIX_ENABLED:
            logger.info("⚠️  APISIX integration is disabled (IS_APISIX_ENABLED=False)")
            return {}

        routes = self.extract_routes_from_fastapi(app)

        # Manually add openapi.json and redoc routes if they're configured and not already extracted
        # Check if they already exist in the routes list
        existing_paths = {route["path"] for route in routes}

        if app.openapi_url and app.openapi_url not in existing_paths:
            routes.append(
                {
                    "path": app.openapi_url,
                    "methods": ["GET"],
                    "name": "openapi_json",
                    "tags": [],
                }
            )
        if app.redoc_url and app.redoc_url not in existing_paths:
            routes.append(
                {
                    "path": app.redoc_url,
                    "methods": ["GET"],
                    "name": "redoc",
                    "tags": [],
                }
            )
        
        # Add apisix.csv route
        apisix_csv_path = f"/{self.base_config.SERVICE_NAME}/apisix.csv"
        if apisix_csv_path not in existing_paths:
            routes.append(
                {
                    "path": apisix_csv_path,
                    "methods": ["GET"],
                    "name": "apisix_csv",
                    "tags": [],
                }
            )

        results = {}

        # Log public paths configuration
        if self.base_config.APISIX_PUBLIC_PATHS:
            public_paths = [
                p.strip()
                for p in self.base_config.APISIX_PUBLIC_PATHS.split(",")  # pylint: disable=no-member
            ]
            logger.info(f"🔓 Public paths (no auth): {', '.join(public_paths)}")
        else:
            logger.info(
                "🔐 No public paths configured - all routes require authentication"
            )

        logger.info(
            f"🚀 Starting individual route registration for {len(routes)} routes..."
        )

        # Prepare all route configs first
        route_tasks = []
        for route_info in routes:
            route_path = route_info["path"]
            route_name = route_info["name"]
            methods = route_info["methods"]

            # Create unique route ID for APISIX (sanitized for special characters)
            sanitized_name = self._sanitize_route_id(route_name)
            route_id = f"{self.config.APISIX_ROUTE_NAME}_{sanitized_name}"

            # Build full URI - check if service name is already in the path
            # FastAPI routes might already include the service name prefix
            if route_path.startswith(f"/{self.base_config.SERVICE_NAME}/"):
                full_uri = route_path  # Already has service name prefix
            else:
                full_uri = f"/{self.base_config.SERVICE_NAME}{route_path}"

            # Replace path parameters with wildcards for APISIX
            # e.g., /api/v1/workspace/{workspace_id}/ -> /api/v1/workspace/*/
            full_uri = self._replace_path_params_with_wildcard(full_uri)

            # Check if this is a public route (no authentication required)
            is_public = self._is_public_path(full_uri)

            # Get plugins for this route (public routes won't have RBAC)
            plugins = self._get_default_plugins(is_public=is_public)
            if custom_plugins and route_path in custom_plugins:
                plugins.update(custom_plugins[route_path])

            # But NOT for documentation routes (docs, openapi.json, redoc) which FastAPI serves with prefix
            # APISIX sends: /demo-management-service/api/v1/health
            # FastAPI expects: /api/v1/health (without prefix for API routes)
            # But for docs: FastAPI expects /demo-management-service/docs (with prefix)

            # Build route configuration
            route_config = {
                "name": route_id,
                "uri": full_uri,
                "methods": methods,
                "upstream": {
                    "type": "roundrobin",
                    "scheme": "http",
                    "nodes": {
                        f"{self.base_config.SERVICE_NAME}:{self.base_config.APP_PORT}": 1
                    },
                },
                "plugins": plugins,
                "status": 1,
            }

            # Add task for concurrent execution
            route_tasks.append((route_id, route_config, route_info, route_path))

        # Register all routes concurrently
        registration_results = await asyncio.gather(
            *[
                self._register_single_route(task[0], task[1], task[2])
                for task in route_tasks
            ],
            return_exceptions=True,
        )

        # Build results dict
        for i, (route_id, route_config, route_info, route_path) in enumerate(
            route_tasks
        ):
            result = registration_results[i]
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to register {route_path}: {result}")
                results[route_path] = False
            else:
                results[route_path] = result

        # Summary
        successful = sum(1 for v in results.values() if v)
        logger.info(
            f"📊 Route registration complete: {successful}/{len(routes)} successful"
        )

        # Generate CSV file with registered routes
        await self._generate_routes_csv(route_tasks)

        return results

    async def _register_single_route(
        self, route_id: str, route_config: Dict[str, Any], route_info: Dict[str, Any]
    ) -> bool:
        """
        Register a single route in APISIX.

        Args:
            route_id: Unique route identifier
            route_config: APISIX route configuration
            route_info: Original route information from FastAPI

        Returns:
            bool: True if registration successful, False otherwise
        """
        admin_url = f"{self.config.APISIX_ADMIN_URL}/apisix/admin/routes/{route_id}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    admin_url, headers=self.headers, json=route_config
                )

                if response.status_code in [200, 201]:
                    # Check if route has RBAC plugin to determine if it's public
                    is_public = "rbac_abac_workspace" not in route_config.get(
                        "plugins", {}
                    )
                    auth_status = "🔓 PUBLIC" if is_public else "🔐 PROTECTED"

                    logger.info(
                        f"✅ {auth_status}: {route_config['uri']} "
                        f"[{', '.join(route_info['methods'])}]"
                    )
                    return True

                logger.error(
                    f"❌ Failed to register {route_config['uri']}: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                return False

        except httpx.ConnectError as e:
            logger.error(
                f"❌ Failed to connect to APISIX Admin API at "
                f"{self.config.APISIX_ADMIN_URL}: {e}"
            )
            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error registering route {route_id}: {e}")
            return False

    async def delete_all_service_routes(self) -> bool:
        """
        Delete all routes for this service from APISIX.

        Returns:
            bool: True if all deletions successful, False otherwise
        """
        try:
            # Get list of all routes
            list_url = f"{self.config.APISIX_ADMIN_URL}/apisix/admin/routes"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(list_url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"❌ Failed to list routes: {response.status_code}")
                    return False

                data = response.json()
                routes = (
                    data.get("list", [])
                    if "list" in data
                    else data.get("node", {}).get("nodes", [])
                )

                # Filter routes that belong to this service
                service_routes = [
                    route
                    for route in routes
                    if route.get("value", {})
                    .get("name", "")
                    .startswith(self.config.APISIX_ROUTE_NAME)
                ]

                if not service_routes:
                    logger.info("ℹ️  No routes found for this service")
                    return True

                # Delete each route
                all_deleted = True
                for route in service_routes:
                    route_key = route.get("key", "").split("/")[-1]
                    delete_url = f"{self.config.APISIX_ADMIN_URL}/apisix/admin/routes/{route_key}"

                    delete_response = await client.delete(
                        delete_url, headers=self.headers
                    )

                    if delete_response.status_code in [200, 204]:
                        logger.info(f"✅ Deleted route: {route_key}")
                    else:
                        logger.error(f"❌ Failed to delete route: {route_key}")
                        all_deleted = False

                return all_deleted

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error deleting service routes: {e}")
            return False

    async def list_service_routes(self) -> List[Dict[str, Any]]:
        """
        List all routes registered for this service in APISIX.

        Returns:
            List of route information dictionaries
        """
        try:
            list_url = f"{self.config.APISIX_ADMIN_URL}/apisix/admin/routes"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(list_url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"❌ Failed to list routes: {response.status_code}")
                    return []

                data = response.json()
                all_routes = (
                    data.get("list", [])
                    if "list" in data
                    else data.get("node", {}).get("nodes", [])
                )

                # Filter routes that belong to this service
                service_routes = []
                for route in all_routes:
                    route_value = route.get("value", {})
                    route_name = route_value.get("name", "")

                    if route_name.startswith(self.config.APISIX_ROUTE_NAME):
                        route_info = {
                            "id": route.get("key", "").split("/")[-1],
                            "name": route_name,
                            "uri": route_value.get("uri", ""),
                            "methods": route_value.get("methods", []),
                            "status": route_value.get("status", 0),
                        }
                        service_routes.append(route_info)

                logger.info(
                    f"📋 Found {len(service_routes)} routes for this service in APISIX"
                )
                return service_routes

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error listing service routes: {e}")
            return []

    async def get_route_details(self, route_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific route.

        Args:
            route_id: The APISIX route ID

        Returns:
            Route details dictionary or None if not found
        """
        try:
            route_url = f"{self.config.APISIX_ADMIN_URL}/apisix/admin/routes/{route_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(route_url, headers=self.headers)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("value", data.get("node", {}).get("value", {}))
                if response.status_code == 404:
                    logger.warning(f"⚠️  Route not found: {route_id}")
                    return None
                logger.error(f"❌ Failed to get route details: {response.status_code}")
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error getting route details: {e}")
            return None

    async def register_route(self) -> bool:
        """
        Register the service route with APISIX Gateway.

        Returns:
            bool: True if registration successful, False otherwise
        """
        if not self.config.IS_APISIX_ENABLED:
            logger.info("⚠️  APISIX integration is disabled (IS_APISIX_ENABLED=False)")
            return False

        # Build the route configuration
        route_config = {
            "name": self.config.APISIX_ROUTE_NAME,
            "uri": f"/{self.base_config.SERVICE_NAME}/*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
            "upstream": {
                "type": "roundrobin",
                "scheme": "http",
                "nodes": {
                    f"{self.base_config.SERVICE_NAME}:{self.base_config.APP_PORT}": 1
                },
            },
            "plugins": {
                "cors": {
                    "allow_origins": (
                        "http://localhost,http://localhost:80,http://localhost:3000,"
                        "http://localhost:8080,http://127.0.0.1,http://127.0.0.1:80,"
                        "http://127.0.0.1:3000,http://127.0.0.1:8080,"
                        "http://articleinnovator.com,http://www.articleinnovator.com,"
                        "https://articleinnovator.com,https://www.articleinnovator.com,"
                        "http://botxbyte.com,http://www.botxbyte.com,"
                        "https://botxbyte.com,https://www.botxbyte.com,"
                        "https://claude.ai,https://www.claudeusercontent.com"
                    ),
                    "allow_methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD",
                    "allow_headers": (
                        "Content-Type,Authorization,X-Correlation-ID,Accept,Origin,"
                        "X-Requested-With,X-API-KEY,Cache-Control,Pragma,Expires,DNT,"
                        "User-Agent,Keep-Alive,If-Modified-Since,X-CustomHeader,"
                        "workspace-id,user-id"
                    ),
                    "expose_headers": (
                        "Content-Length,Content-Type,X-Correlation-ID,Authorization"
                    ),
                    "allow_credential": True,
                    "max_age": 86400,
                },
                "rbac_abac_workspace": {"jwt_secret": self.config.APISIX_JWT_SECRET},
            },
            "status": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    self.admin_url, headers=self.headers, json=route_config
                )

                if response.status_code in [200, 201]:
                    logger.info(
                        f"✅ Successfully registered route '{self.config.APISIX_ROUTE_NAME}' "
                        f"with APISIX Gateway"
                    )
                    logger.info(f"   Route URI: /{self.base_config.SERVICE_NAME}/*")
                    logger.info(
                        f"   Upstream: {self.base_config.SERVICE_NAME}:{self.base_config.APP_PORT}"
                    )
                    logger.info("   Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS")
                    return True

                logger.error(
                    f"❌ Failed to register APISIX route. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False

        except httpx.ConnectError as e:
            logger.error(
                f"❌ Failed to connect to APISIX Admin API at {self.config.APISIX_ADMIN_URL}: {e}"
            )
            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error registering APISIX route: {e}")
            return False

    async def check_route_exists(self) -> bool:
        """
        Check if the route already exists in APISIX.

        Returns:
            bool: True if route exists, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.admin_url, headers=self.headers)
                return response.status_code == 200
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    async def delete_route(self) -> bool:
        """
        Delete the service route from APISIX Gateway.

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(self.admin_url, headers=self.headers)

                if response.status_code in [200, 204]:
                    logger.info(
                        f"✅ Successfully deleted route '{self.config.APISIX_ROUTE_NAME}' "
                        f"from APISIX"
                    )
                    return True

                logger.error(
                    f"❌ Failed to delete APISIX route. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"❌ Error deleting APISIX route: {e}")
            return False


# Global instance
_apisix_helper: APISIXHelper | None = None


def get_apisix_helper() -> APISIXHelper:
    """Get the APISIX helper instance."""
    global _apisix_helper  # pylint: disable=global-statement
    if _apisix_helper is None:
        _apisix_helper = APISIXHelper()
    return _apisix_helper
