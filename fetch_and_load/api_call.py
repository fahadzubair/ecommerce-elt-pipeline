import requests

API_ENDPOINTS = [
    "https://services.odata.org/v4/northwind/northwind.svc/Customers",
    "https://services.odata.org/v4/northwind/northwind.svc/Orders",
    "https://services.odata.org/v4/northwind/northwind.svc/Order_Details",
    "https://services.odata.org/v4/northwind/northwind.svc/Products",
    "https://services.odata.org/v4/northwind/northwind.svc/Categories",
    "https://services.odata.org/v4/northwind/northwind.svc/Suppliers",
    "https://services.odata.org/v4/northwind/northwind.svc/Employees",
    "https://services.odata.org/v4/northwind/northwind.svc/Shippers",
    "https://services.odata.org/v4/northwind/northwind.svc/Regions",
    "https://services.odata.org/v4/northwind/northwind.svc/Territories",
]


def api_caller():
    """Fetch every endpoint and return {table_name: parsed_json}. No local files."""
    datasets = {}

    for i, endpoint in enumerate(API_ENDPOINTS, start=1):

        # Increase the record cap by 100 for each call, starting at 100.
        limit = i * 100

        # GET request
        response = requests.get(endpoint, params={"$top": limit})
        response.raise_for_status()
        data = response.json()

        name = endpoint.split('/')[-1].lower()
        datasets[name] = data

        print(f"Fetched {len(data.get('value', []))} rows from {name} endpoint (limit={limit})")

    return datasets

