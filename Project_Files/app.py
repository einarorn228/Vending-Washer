import requests
import random
import string
from flask import Flask, jsonify, request
from models import session, Code  # Import your SQLAlchemy session and Code model

app = Flask(__name__)

def generate_random_code(length=8):
    """Generate a random alphanumeric code of specified length using digits, uppercase, and lowercase letters."""
    characters = string.ascii_letters + string.digits  # Includes uppercase, lowercase, and digits
    return ''.join(random.choices(characters, k=length))

def is_code_unique(code_value):
    """Check if the generated code already exists in the database."""
    existing_code = session.query(Code).filter_by(code=code_value).first()
    return existing_code is None

def generate_unique_code(length=8):
    """Generate a unique QR code that doesn't already exist in the database."""
    while True:
        random_code = generate_random_code(length)
        if is_code_unique(random_code):
            return random_code

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
        # Parse the request body
        data = request.get_json(force=True)
        
        if not data or "order_id" not in data:
            return jsonify({"error": "Invalid input"}), 400

        order_id = data["order_id"]

        # Check if the order ID already exists in the database
        existing_code = session.query(Code).filter_by(order_id=order_id).first()
        if existing_code:
            return jsonify({
                "error": "Order ID already exists",
                "code": existing_code.code,
                "usage_limit": existing_code.usage_limit,
                "current_usage": existing_code.current_usage
            }), 400

        # Generate a new unique QR code
        random_code = generate_unique_code()

        # Fetch the simulated usage info from the external API
        usage_info = get_usage_info()

        if not usage_info:
            return jsonify({"error": "Failed to fetch usage info"}), 500

        # Save the code, order_id, and usage information to the database
        new_code = Code(code=random_code, order_id=order_id, usage_limit=usage_info['usage_limit'])
        session.add(new_code)
        session.commit()

        return jsonify({
            "message": "QR code generated successfully.",
            "code": random_code,
            "order_id": order_id,
            "usage_info": {
                "usage_limit": usage_info['usage_limit'],
                "current_usage": 0
            }
        }), 201

    except Exception as e:
        return jsonify({"error": "Failed to process request", "details": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)

