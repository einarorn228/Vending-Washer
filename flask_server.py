from flask import Flask, jsonify, request
from controllers.code_generator import generate_new_code
from utils.logger import logger

app = Flask(__name__)

@app.route('/generate_code', methods=['POST'])
def generate_code():
    """Endpoint to generate a new QR code based on an order ID."""
    try:
        # Parse the request body
        data = request.get_json(force=True)

        # Get data from body
        order_id = data.get("order_id")
        usage_limit = data.get("usage_limit")
        
        # Error handling
        if not order_id or usage_limit is None:
            return jsonify({"error": "Missing order_id or usage_limit"}), 400
        
        # Generate the code using the refactored logic
        response = generate_new_code(order_id, usage_limit)
        logger.info("Generated code for order %s", order_id)
        return jsonify(response), response['status_code']

    except Exception:
        logger.exception("Failed to process /generate_code request")
        return jsonify({"error": "Failed to process request"}), 400
