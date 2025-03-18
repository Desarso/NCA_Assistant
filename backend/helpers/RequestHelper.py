import threading
import time
import requests
import json
from typing import Tuple, Optional, Dict, Any
import logging
import os
from dotenv import load_dotenv

load_dotenv()

tenant_id = os.getenv("TENANT_ID")
client_id = os.getenv("APP_ID")
client_secret = os.getenv("SECRET")


_token = None
_headers = {}
_token_expiry = None
_token_lock = threading.Lock()


def refresh_token() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:

    # print credentials
    print("tenant_id", tenant_id)
    print("client_id", client_id)
    print("client_secret", client_secret)
    """Refreshes the access token for Microsoft Graph API"""
    global _token, _headers, _token_expiry

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }

    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in")  # Get token lifetime

        if not token:
            print(response.text)
            logging.error("Failed to get token: " + response.text)
            return None, {"error": "Failed to get token", "details": response.text}

        # Update the global token variables
        _token = token
        _headers = {
            "Authorization": f"Bearer {_token}",
            "Content-Type": "application/json"
        }
        _token_expiry = time.time() + int(expires_in)
        logging.info("Token refreshed successfully.")

        return _token, None

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None, {"error": "Failed to refresh token", "details": str(e)}
    except Exception as e:
        logging.exception("An unexpected error occurred during token refresh.")
        return None, {"error": "Unexpected error during token refresh", "details": str(e)}

def _check_and_refresh_token() -> Optional[Dict[str, Any]]:
    """Checks if the token is expired and refreshes it if needed."""
    global _token, _headers, _token_expiry

    if _token_expiry is None or time.time() >= _token_expiry:
        logging.info("Token expired or about to expire. Refreshing...")
        with _token_lock:
            token, error = refresh_token()
            if error:
                return error  # Return the error encountered during refresh

            # Update global token variables if refresh was successful
            if token:
                _token = token
                _headers["Authorization"] = f"Bearer {_token}"
                schedule_token_refresh()

    return None # No error


def schedule_token_refresh():
    """Schedules the token refresh to occur before it expires."""
    global _token_expiry

    if _token_expiry:
        # Refresh token 5 minutes before expiry
        refresh_time = _token_expiry - time.time() - 300
        if refresh_time > 0:
            logging.info(f"Scheduling token refresh in {refresh_time} seconds.")
            threading.Timer(refresh_time, _refresh_token_and_reschedule).start()
        else:
            logging.warning("Token is already expired or about to expire. Refreshing now.")
            _refresh_token_and_reschedule()
    else:
        logging.warning("Token expiry not set. Refreshing immediately.")
        _refresh_token_and_reschedule()

def _refresh_token_and_reschedule():
    """Refreshes the token and reschedules the next refresh."""
    global _token, _headers

    with _token_lock:  # Ensure thread safety
        token, error = refresh_token()
        if error:
            logging.error(f"Failed to refresh token: {error}")
            # Handle the error (e.g., stop the application or retry later)
            return

        if token:
            _token = token
            _headers["Authorization"] = f"Bearer {_token}"
            schedule_token_refresh()


def make_request(method: str, url: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Helper function to make requests to the Graph API."""
    global _headers

    # Check if token needs refreshing before making the request
    token_error = _check_and_refresh_token()
    if token_error:
        return None, token_error

    try:
        if headers is None:
            headers = _headers

        response = requests.request(method, url, headers=headers, json=json_data)
        response.raise_for_status()
        if response.status_code == 204:
            return None, None # No content returned
        return response.json(), None # Return json and no error

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None, {"error": "Request failed", "details": str(e)}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON: {e}")
        return None, {"error": "Failed to decode JSON", "details": str(e), "response_text": response.text}
    except Exception as e:
        logging.exception("An unexpected error occurred during request.")
        return None, {"error": "Unexpected error during request", "details": str(e)}

