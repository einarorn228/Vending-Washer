import requests

def get_usage_info():
    """Fetch QR code usage information from the external application."""
    url = "https://run.mocky.io/v3/58f982af-323d-4f50-8cf3-755fa630f664"  # Replace with your actual API endpoint
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()  # Return the data as JSON if the request is successful
    else:
        print(f"Error fetching data: {response.status_code}")
        return None