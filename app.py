from flask import Flask, request, jsonify
import logging
from logging.handlers import RotatingFileHandler
import functions_new
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address)
# Set up CORS
CORS(app, resources={r"/*": {"origins": "*"}})
# CORS(app, resources={r"/*": {"origins": ["https://mi.arepa.digital", "https://another.allowed.origin"]}})

# Set up logging
handler = RotatingFileHandler('error.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.ERROR)
app.logger.addHandler(handler)

@app.route('/handle_update', methods=['POST'])
@limiter.limit("5 per minute")  # Limit to 5 requests per minute per IP
def handle_update():
    try:
        data = request.get_json()
        if not data:
            app.logger.error('Invalid payload: No data received')
            return jsonify({"error": "Invalid payload"}), 400

        order_id = data.get('order_id')
        status = data.get('status')
        signer_id = data.get('signer_id')
        owner_id = data.get('owner_id')
        type = data.get('type')

        if None in [order_id, status, signer_id, owner_id, type]:
            app.logger.error(f'Invalid payload: {data}')
            return jsonify({"error": "Invalid payload"}), 400

        # Call the function to handle the update
        functions_new.handle_update(order_id, status, signer_id, owner_id, type)

        return jsonify({"message": "Success"}), 200

    except Exception as e:
        app.logger.error('An error occurred: %s', e)
        return jsonify({"error": "Internal Server Error"}), 500

# if __name__ == '__main__':
#     app.run(debug=True)
    
