import asyncio
import httpx

async def delete_all_routes():
    base_url = "http://157.230.202.182:9180/apisix/admin/routes"
    api_key = "edd1c9f034335f136f87ad84b625c8f1"
    headers = {"X-API-KEY": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        # Get all routes
        response = await client.get(base_url)
        data = response.json()
        routes = data.get('list', [])
        
        # Delete all routes concurrently
        tasks = []
        for route in routes:
            route_id = route['value']['id']
            delete_url = f"{base_url}/{route_id}"
            print(f"Deleting route: {route_id}")
            tasks.append(client.delete(delete_url))
        
        # Wait for all deletions to complete
        await asyncio.gather(*tasks)
        print(f"\n✅ Deleted {len(tasks)} routes")

if __name__ == "__main__":
    asyncio.run(delete_all_routes())