import requests

base_url = "http://157.230.202.182:9180/apisix/admin/routes"
api_key = "edd1c9f034335f136f87ad84b625c8f1"
headers = {"X-API-KEY": api_key}

# Get all routes
response = requests.get(base_url, headers=headers)
routes = response.json().get('list', [])

# Delete each route
for route in routes:
    route_id = route['value']['id']
    delete_url = f"{base_url}/{route_id}"
    print(f"Deleting route: {route_id}")
    requests.delete(delete_url, headers=headers)