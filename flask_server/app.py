from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import jwt
import time
from datetime import datetime
from functools import wraps
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from utilities.db_config import POSTGRES_CONFIG
import json
from urllib.parse import urlparse
import os
import sys
from dotenv import load_dotenv

# === Setup Logging ===
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see all logs including IP addresses
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        logging.FileHandler("everify_server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_base_dir, '.env'))

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
PUBLIC_API_KEY = os.getenv('PUBLIC_API_KEY')
BASE_URL = 'https://ws.everify.gov.ph/api'

access_token = None
token_expiry = None

# Store full_aname in memory for PySide6 to access
shared_data = {
    "full_name" : None
}

def start_server():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


def is_token_expired():
    """
    Check if the current access token is expired or not available.
    Returns True if the token is expired or not set.
    """
    global token_expiry

    if token_expiry is None:
        # print("⚠️ Token expiry not set — assuming token is expired.")
        logger.warning("Token expiry not set — assuming token is expired.")
        return True

    current_time = int(time.time())
    is_expired = current_time >= token_expiry

    if is_expired:
        # print(f"🔒 Access token expired at {token_expiry}, current time is {current_time}")
        logger.info(f"Access token expired at {token_expiry}, current time is {current_time}")
    else:
        # print(f"✅ Access token still valid. Expires at {token_expiry}, current time is {current_time}")
        logger.debug(f"Access token still valid. Expires at {token_expiry}, current time is {current_time}")

    return is_expired


def refresh_token():
    """
    Refresh the access token by making a request to the authentication endpoint.
    """
    global access_token, token_expiry

    try: 
        response = requests.post(
            f'{BASE_URL}/auth',
            json={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=10
        )
        if response.status_code == 200:
            response.raise_for_status()
            response_json = response.json()
            access_token = response_json["data"]["access_token"]
            token_expiry = int(response_json["data"]["expires_at"])
            # print(f"🔁 New access token received. Expires at: {token_expiry}")
            logger.info(f"New access token received. Expires at: {token_expiry}")
            return access_token
        else:
            logger.error(f"Failed to refresh token. Status code: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            return None
        
    except requests.exceptions.ReadTimeout:
        app.logger.error("Timeout: eVerify server did not respond within 10 seconds.")
        return jsonify({"error": "eVerify server timeout. Please try again later."}), 504  # Gateway Timeout

    except Exception as e:
        # print(f"❌ Token refresh failed: {str(e)}")
        logger.exception("Exception occurred while refreshing token.")
        return None


def get_access_token():
    """
    Get the current access token, refreshing it if necessary.
    """
    global access_token, token_expiry
    
    if is_token_expired():
        try:
            payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            response = requests.post(f'{BASE_URL}/auth', json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Token response data: {data}")

                access_token = data['data']['access_token']
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                token_expiry = int(decoded["exp"])

                logger.info(f"Access token refreshed successfully. New expiry: {token_expiry}")
                return access_token
            else:
                logger.error(f"Failed to get access token. Status code: {response.status_code}")
                logger.debug(f"Response content: {response.text}")
                return None
            
        except requests.exceptions.ReadTimeout:
            app.logger.error("Timeout: eVerify server did not respond within 10 seconds.")
            return jsonify({"error": "eVerify server timeout. Please try again later."}), 504  # Gateway Timeout
        
        except Exception as e:
            # print(f"❌ Access token error: {str(e)}")
            logger.exception("Exception occurred while getting access token.")
            return None
    else:
        return access_token

# Retry decorator
def retry_request(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    print(f"⚠️ Attempt {attempt} failed: {e}")
                    if attempt < max_retries:
                        time.sleep(delay)
            return jsonify({"error": "Max retries exceeded"}), 500
        return wrapper
    return decorator

def get_db_connection():
    """Create a new database connection"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def close_db_connection(conn, cursor=None):
    """Safely close database connection and cursor"""
    try:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")

@app.route('/query', methods=['POST'])
@retry_request()
def verify():
    payload = request.json
    token = get_access_token()  # Always fetch latest valid token

    if not token:
        return jsonify({"error": "Authentication failed."}), 401

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(f"{BASE_URL}/query", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), response.status_code

    except requests.exceptions.ReadTimeout:
        logger.error("Timeout: eVerify server did not respond within 10 seconds.")
        return jsonify({"error": "eVerify server timeout. Please try again later."}), 504
    
    except Exception as e:
        logger.exception("Exception occurred during /query request.")
        return jsonify({"error": "Internal server error."}), 500

@app.route('/query/qr/check', methods=['POST'])
@retry_request()
def qr_check():
    token = get_access_token()

    if not token:
        return jsonify({"error": "Authentication failed."}), 401

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        data = request.json
        response = requests.post(f"{BASE_URL}/query/qr/check", headers=headers, json=data, timeout=10)
        logger.debug(f"QR check response: {response.json()}, requests: {response.request}, Public_IP: {get_public_ip()}")
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    
    except requests.exceptions.ReadTimeout:
        logger.error("Timeout: eVerify server did not respond within 10 seconds.")
        return jsonify({"error": "eVerify server timeout. Please try again later."}), 504
    
    except Exception as e:
        logger.exception("Exception occurred during /query/qr request.")
        return jsonify({"error": "Internal server error."}), 500

@app.route('/query/qr', methods=['POST'])
@retry_request()
def qr_verify():
    token = get_access_token()

    if not token:
        return jsonify({"error": "Authentication failed."}), 401

    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        data = request.json
        response = requests.post(f"{BASE_URL}/query/qr", headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    
    except requests.exceptions.ReadTimeout:
        logger.error("Timeout: eVerify server did not respond within 10 seconds.")
        return jsonify({"error": "eVerify server timeout. Please try again later."}), 504
    
    except Exception as e:
        logger.exception("Exception occurred during /query/qr/check request.")
        return jsonify({"error": "Internal server error."}), 500

@app.route('/liveness')
def liveness_page():
    return render_template('liveness.html')

# Store the session ID in memory (for testing; use DB in prod)
liveness_result_data = {}

@app.route("/liveness_result", methods=["POST"])
def post_liveness_result():
    data = request.json
    session_id = data.get("face_liveness_session_id")
    if session_id:
        liveness_result_data["id"] = session_id
        logger.info(f"Liveness session ID stored: {session_id}")
        return jsonify({"message": "Saved."}), 200
    
    logger.warning("No session ID provided in POST to /liveness_result.")
    return jsonify({"error": "Missing session ID"}), 400

@app.route("/liveness_result", methods=["GET"])
def get_liveness_result():
    session_id = liveness_result_data.get("id")
    if session_id:
        logger.debug(f"Returning liveness session ID: {session_id}")
        return jsonify({"face_liveness_session_id": session_id})
    
    logger.debug("No session ID stored yet.")
    return jsonify({}), 204  # No content yet

@app.route("/liveness_result", methods=["DELETE"])
def delete_liveness_result():
    if "id" in liveness_result_data:
        logger.info(f"Clearing stored liveness session ID: {liveness_result_data['id']}")
        liveness_result_data.clear()
        return jsonify({"message": "Liveness session ID cleared"}), 200
    return jsonify({"message": "No liveness session ID to clear"}), 204

@app.route('/store_verification', methods=['POST'])
def store_verification():
    try:
        payload = request.get_json()
        wrapper = payload.get('data')
        if not wrapper:
            return jsonify({'error': 'Missing wrapper'}), 400

        person = wrapper.get('data', {})

        # Download and save the face image
        face_url = person.get('face_url')
        face_key = None

        if face_url:
            try:
                # Extract filename (e.g., "2812742641908201.jpg")
                filename = os.path.basename(urlparse(face_url).path)
                face_key = filename

                # Get the absolute path to the images directory
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                images_dir = os.path.join(base_dir, "images", "faces")
                os.makedirs(images_dir, exist_ok=True)
                
                local_path = os.path.join(images_dir, filename)
                logger.info(f"Attempting to save face image to: {local_path}")
                
                # Download and save
                response = requests.get(face_url, stream=True)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Successfully saved face image to: {local_path}")
                
            except Exception as e:
                logger.error(f"Error downloading/saving face image: {str(e)}")
                # Continue with the verification process even if face image fails
                face_key = None

        # Now extract from person, not from wrapper
        values = (
            person.get('reference'),
            person.get('code'),
            person.get('first_name'),
            person.get('middle_name'),
            person.get('last_name'),
            person.get('birth_date'),
            face_key,
            person.get('gender'),
            person.get('marital_status'),
            person.get('municipality'),
            person.get('province')
        )
        logger.info("Inserting verification record with values: %s", values)

        # Connect to PostgreSQL and insert the record
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO verifications (
                    reference, code, first_name, middle_name, last_name, birth_date,
                    face_key, gender, marital_status, municipality, province
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', values)
            
            return jsonify({'message': 'Verification stored successfully'}), 200

        except Exception as e:
            logger.error(f"Database error while storing verification: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Error in store_verification: {str(e)}")
        return jsonify({'error': str(e)}), 500


def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=text", timeout=5)
        if response.status_code == 200:
            return response.text
        else:
            return "Unable to fetch IP"
    except Exception as e:
        return f"Error: {e}"

# Example usage
public_ip = get_public_ip()
print("Public IP:", public_ip)
logger.info(f"Server Public IP: {public_ip}")


# if __name__ == '__main__':
#     app.run(debug=True, port=5000)

if __name__ == "__main__":
    start_server()


