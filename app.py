import requests
import random
import string
from flask import Flask, jsonify, request

app = Flask(__name__)

def generate_random_code(length=8):
    """Generate a random alphanumeric code of specified length using digits, uppercase, and lowercase letters."""
    characters = string.ascii_letters + string.digits  # Includes uppercase, lowercase, and digits
    return ''.join(random.choices(characters, k=length))

def get_usage_info():
    """Fetch QR code usage information from the external application."""
    url = "https://run.mocky.io/v3/58f982af-323d-4f50-8cf3-755fa630f664"  # Replace with your actual API endpoint
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()  # Return the data as JSON if the request is successful
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

@app.route('/generate_code', methods=['POST'])
def generate_code():
    try:
        # Attempt to parse the JSON request body
        data = request.get_json(force=True)
        
        if not data or "order_id" not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        # Generate a new random code 
        random_code = generate_random_code()  # Example code

        # Simulated usage info 
        usage_info = get_usage_info()

        linked_info = {
            "code": random_code,
            "usage_limit": usage_info['usage_limit'],
            "current_usage": 0
        }

        return jsonify({
            "message": "QR code generated successfully.",
            "code": random_code,
            "usage_info": linked_info
        }), 201

    except Exception as e:
        return jsonify({"error": "Failed to process request", "details": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
