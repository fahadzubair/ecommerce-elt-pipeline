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

    for endpoint in API_ENDPOINTS:

        # GET request
        response = requests.get(endpoint)
        data = response.json()

        name = endpoint.split('/')[-1].lower()
        datasets[name] = data

        print(f"Fetched {len(data.get('value', []))} rows from {name} endpoint")

    return datasets

