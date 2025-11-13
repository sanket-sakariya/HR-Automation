import requests
import csv
import json
import os
import re
import uuid
from dotenv import load_dotenv

def fetch_openapi_schema(url: str):
    """Fetches the OpenAPI schema from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching schema: {e}")
        return None

def simplify_schema(schema_component: dict, definitions: dict):
    """Recursively generates an example from a JSON schema component."""
    if not schema_component:
        return None

    if 'schema' in schema_component:
        return simplify_schema(schema_component['schema'], definitions)

    if '$ref' in schema_component:
        ref_name = schema_component['$ref'].split('/')[-1]
        return simplify_schema(definitions.get(ref_name, {}), definitions)

    if 'example' in schema_component:
        return schema_component['example']
    
    if 'default' in schema_component:
        return schema_component['default']

    schema_type = schema_component.get('type')

    if schema_type == 'object':
        if 'properties' not in schema_component:
            return {}
        example = {}
        for prop_name, prop_details in schema_component.get('properties', {}).items():
            example[prop_name] = simplify_schema(prop_details, definitions)
        return example
    elif schema_type == 'array':
        if 'items' in schema_component:
            # Generate one example item for the array
            return [simplify_schema(schema_component['items'], definitions)]
        else:
            return []
    elif schema_type == 'string':
        if 'enum' in schema_component:
            return schema_component['enum'][0]
        if 'format' in schema_component:
            if schema_component['format'] == 'date-time':
                return "2023-01-01T12:00:00Z"
            if schema_component['format'] == 'date':
                return "2023-01-01"
            if schema_component['format'] == 'email':
                return "user@example.com"
            if schema_component['format'] == 'uri':
                return "https://example.com"
            if schema_component['format'] == 'uuid':
                return str(uuid.uuid4())
        return "string"
    elif schema_type == 'integer':
        return 0
    elif schema_type == 'number':
        return 0.0
    elif schema_type == 'boolean':
        return False
    
    # Fallback for unknown types
    return None

def execute_request(base_url: str, method: str, endpoint: str, data: str, headers: dict):
    """Executes an HTTP request and returns the status code and response."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    print(f"Executing {method} {url} with headers: {headers}")

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=data)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, data=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            return 'N/A', f'Unsupported method: {method}'
        
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return 'Error', str(e)

def generate_csv_from_schema(schema: dict, output_filename: str, base_url: str):
    """Generates a CSV file from the OpenAPI schema and tests the endpoints."""
    # Pre-scan for all path parameter names
    path_param_names = set()
    for path in schema.get('paths', {}):
        params = re.findall(r'\{(\w+)\}', path)
        path_param_names.update(params)
    if path_param_names:
        print(f"Found path parameters: {path_param_names}")

    created_ids = {}

    static_user_id = str(uuid.uuid4())
    static_workspace_id = str(uuid.uuid4())

    with open(output_filename, 'w', newline='') as csvfile:
        fieldnames = ['tags', 'summary', 'endpoint', 'status_code', 'method', 'request_body_schema', 'response']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Flatten all operations from the schema
        all_operations = []
        for path, path_item in schema.get('paths', {}).items():
            for method, operation in path_item.items():
                all_operations.append({'path': path, 'method': method, 'operation': operation})

        # Define a sorting key for the operations
        def get_operation_order(op):
            path_lower = op['path'].lower()
            method_upper = op['method'].upper()

            # Create
            if method_upper == 'POST' and 'create' in path_lower:
                return 0
            # List
            if method_upper == 'GET' and '{' not in path_lower and 'health' not in path_lower:
                return 1
            # Read
            if method_upper == 'GET' and '{' in path_lower:
                return 2
            # Update
            if method_upper in ['PATCH', 'PUT']:
                return 3
            # Delete
            if method_upper == 'DELETE':
                return 4
            # Other POSTs
            if method_upper == 'POST':
                return 5
            # Health check
            if method_upper == 'GET' and 'health' in path_lower:
                return 6
            return 7

        # Sort operations based on the desired logical flow
        sorted_operations = sorted(all_operations, key=get_operation_order)

        for op in sorted_operations:
            path = op['path']
            method = op['method']
            operation = op['operation']

            if 'migrations' in operation.get('tags', []):
                continue

            # Try to substitute path parameters
            formatted_path = path
            path_params_in_current_path = re.findall(r'\{(\w+)\}', path)
            
            if path_params_in_current_path:
                # Check if all required IDs have been captured
                if all(param in created_ids for param in path_params_in_current_path):
                    try:
                        formatted_path = path.format(**created_ids)
                    except KeyError as e:
                        print(f"Skipping endpoint {path} due to missing path parameter: {e}")
                        continue
                else:
                    print(f"Skipping endpoint {path} due to missing path parameters: {set(path_params_in_current_path) - set(created_ids.keys())}")
                    continue

            tags = ", ".join(operation.get('tags', []))
            summary = operation.get('summary', '')
            method_upper = method.upper()

            # Dynamically build headers from OpenAPI spec for each request
            headers = {
                'Content-Type': 'application/json',
                'user-id': static_user_id,
                'workspace-id': static_workspace_id
            }

            request_body_for_request = "{}"
            request_body_schema_simplified = 'No request body'

            if 'requestBody' in operation:
                content = operation['requestBody'].get('content', {})
                if 'application/json' in content:
                    app_json_content = content['application/json']
                    
                    example_to_use = None
                    if 'examples' in app_json_content and 'default' in app_json_content['examples'] and 'value' in app_json_content['examples']['default']:
                        example_to_use = app_json_content['examples']['default']['value']
                    elif 'example' in app_json_content:
                        example_to_use = app_json_content['example']
                    
                    if example_to_use:
                        request_body_for_request = json.dumps(example_to_use)
                        request_body_schema_simplified = request_body_for_request
                    else:
                        ref = app_json_content['schema'].get('$ref')
                        if ref:
                            schema_name = ref.split('/')[-1]
                            schema_component = schema.get('components', {}).get('schemas', {}).get(schema_name)
                            if schema_component:
                                all_schemas = schema.get('components', {}).get('schemas', {})
                                simplified_obj = simplify_schema(schema_component, all_schemas)
                                request_body_for_request = json.dumps(simplified_obj)
                                request_body_schema_simplified = request_body_for_request

            status_code, response_text = execute_request(base_url, method_upper, formatted_path, request_body_for_request, headers)

            # If a resource was created, try to extract its ID
            if method_upper == 'POST' and status_code in [200, 201]:
                try:
                    response_json = json.loads(response_text)
                    
                    def find_and_store_ids(data, param_names, storage):
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if key in param_names and isinstance(value, (str, int, float, bool)):
                                    if key not in storage:
                                        storage[key] = value
                                        print(f"Captured {{'{key}': '{value}'}} from successful POST to {path}")
                                elif isinstance(value, (dict, list)):
                                    find_and_store_ids(value, param_names, storage)
                        elif isinstance(data, list):
                            for item in data:
                                find_and_store_ids(item, param_names, storage)

                    find_and_store_ids(response_json, path_param_names, created_ids)

                except json.JSONDecodeError:
                    pass # Not a JSON response

            writer.writerow({
                'tags': tags,
                'summary': summary,
                'endpoint': formatted_path,
                'method': method_upper,
                'request_body_schema': request_body_schema_simplified,
                'status_code': status_code,
                'response': response_text
            })

if __name__ == "__main__":
    load_dotenv(dotenv_path='.env.dev')
    port = os.getenv("APP_PORT", 8801)

    base_url = f"http://127.0.0.1:{port}"
    openapi_url = f"{base_url}/openapi.json"
    output_csv_file = 'docs/test/all_endpoints_results.csv'
    
    openapi_schema = fetch_openapi_schema(openapi_url)
    
    if openapi_schema:
        generate_csv_from_schema(openapi_schema, output_csv_file, base_url)
        print(f"✅ Successfully generated {output_csv_file}")
