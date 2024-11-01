from flask import Flask, jsonify, request
from controllers.code_generator import generate_new_code

app = Flask(__name__)

@app.route('/generate_code', methods=['POST'])
def generate_code():
    """Endpoint to generate a new QR code based on an order ID."""
    try:
        # Parse the request body
        data = request.get_json(force=True)
        
        if not data or "order_id" not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        # Generate the code using the refactored logic
        response = generate_new_code(data["order_id"])
        return jsonify(response), response['status_code']

    except Exception as e:
        return jsonify({"error": "Failed to process request", "details": str(e)}), 400
