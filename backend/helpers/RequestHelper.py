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
        "scope": "https://graph.microsoft.com/.default",
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
            "Content-Type": "application/json",
        }
        _token_expiry = time.time() + int(expires_in)
        logging.info("Token refreshed successfully.")

        return _token, None

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None, {"error": "Failed to refresh token", "details": str(e)}
    except Exception as e:
        logging.exception("An unexpected error occurred during token refresh.")
        return None, {
            "error": "Unexpected error during token refresh",
            "details": str(e),
        }


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

    return None  # No error


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
            logging.warning(
                "Token is already expired or about to expire. Refreshing now."
            )
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


def make_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Makes an HTTP request using the requests library, handling token refresh
    and returning structured errors including status code and headers on failure.

    Args:
        method: HTTP method (e.g., 'GET', 'POST').
        url: The URL for the request.
        headers: Optional dictionary of headers. Uses global _headers if None.
        json_data: Optional dictionary for the JSON request body.

    Returns:
        tuple: (response_json, None) on success (status 200-299, excluding 204),
               ({}, None) on success with status 204 (No Content),
               (None, error_details) on failure.
               The error_details dictionary will contain 'error', 'details',
               and potentially 'status_code', 'headers', and 'response_text'.
    """
    global _headers
    response: Optional[requests.Response] = (
        None  # Keep track of response for error reporting
    )

    # 1. Check and refresh token
    token_error = _check_and_refresh_token()
    if token_error:
        logging.error(f"Token refresh failed prior to request: {token_error}")
        # Ensure the returned error structure is consistent
        if isinstance(token_error, dict):
            token_error.setdefault("error", "Token refresh failed")
            return None, token_error
        else:
            return None, {"error": "Token refresh failed", "details": str(token_error)}

    # 2. Prepare headers
    request_headers = _headers if headers is None else headers
    if (
        not request_headers
    ):  # Ensure headers are actually set after potential global lookup
        logging.error("Request headers are missing after token check and fallback.")
        return None, {
            "error": "Missing request headers",
            "status_code": 500,
        }  # Internal configuration error

    # 3. Make the request
    try:
        logging.debug(f"Making {method} request to {url}")
        response = requests.request(
            method,
            url,
            headers=request_headers,
            json=json_data,
            timeout=30,  # Add a reasonable timeout
        )

        # Check for HTTP errors (4xx, 5xx)
        response.raise_for_status()

        # Handle successful responses
        if response.status_code == 204:
            logging.debug(f"Request successful with 204 No Content: {method} {url}")
            return (
                {},
                None,
            )  # Return empty dict for No Content, signifying success with no data

        # Attempt to parse JSON for other successful responses (e.g., 200, 201)
        # Note: response.json() can still raise JSONDecodeError if body is not valid JSON
        response_json = response.json()
        logging.debug(
            f"Request successful with status {response.status_code}: {method} {url}"
        )
        return response_json, None

    # 4. Handle specific exceptions
    except requests.exceptions.HTTPError as e:
        # This is raised by response.raise_for_status() for 4xx/5xx errors
        # The 'response' object is guaranteed to be available in 'e.response'
        err_status = e.response.status_code
        err_headers = dict(e.response.headers)  # Get headers as a dict
        err_text = e.response.text  # Get raw response body

        log_msg = (
            f"HTTP Error {err_status} for {method} {url}. Response: {err_text[:500]}"  # Log truncated response
            f"{'...' if len(err_text) > 500 else ''}"
        )
        # Log specific error types differently
        if 400 <= err_status < 500:
            logging.warning(log_msg)  # Client errors as warnings
        else:
            logging.error(log_msg)  # Server errors as errors

        return None, {
            "error": f"HTTP Error: {err_status}",
            "details": str(e),  # Original exception message
            "status_code": err_status,
            "headers": err_headers,
            "response_text": err_text,  # Include response body for debugging
        }

    except requests.exceptions.Timeout as e:
        logging.error(f"Request timed out for {method} {url}: {e}")
        return None, {"error": "Request Timeout", "details": str(e)}

    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error for {method} {url}: {e}")
        return None, {"error": "Connection Error", "details": str(e)}

    except requests.exceptions.RequestException as e:
        # Catch other potential request issues (e.g., URL formatting, invalid headers *before* send)
        # 'response' might be None here
        err_status = None
        err_headers = {}
        err_text = None
        log_msg = f"Generic RequestException for {method} {url}: {e}"

        if hasattr(e, "response") and e.response is not None:
            # If somehow a RequestException has a response (less common for non-HTTPError)
            err_status = e.response.status_code
            err_headers = dict(e.response.headers)
            err_text = e.response.text
            log_msg += f" (Status: {err_status})"

        logging.error(log_msg)
        return None, {
            "error": "Request Failed",
            "details": str(e),
            "status_code": err_status,  # May be None
            "headers": err_headers,  # May be empty
            "response_text": err_text,  # May be None
        }

    except json.JSONDecodeError as e:
        # This happens if raise_for_status passed (e.g., status 200) but the body wasn't valid JSON
        err_status = response.status_code if response else None
        err_headers = dict(response.headers) if response else {}
        err_text = response.text if response else None

        logging.error(
            f"Failed to decode JSON response for {method} {url} (Status: {err_status}): {e}"
        )
        return None, {
            "error": "Failed to decode JSON response",
            "details": str(e),
            "status_code": err_status,  # Include status code if available
            "headers": err_headers,  # Include headers if available
            "response_text": err_text,  # Include the raw text that failed parsing
        }

    except Exception as e:
        # Catch-all for truly unexpected errors
        err_status = response.status_code if response else None
        logging.exception(
            f"An unexpected error occurred during request for {method} {url} (Status: {err_status})"
        )
        return (
            None,
            {
                "error": "Unexpected error during request",
                "details": str(e),
                "status_code": err_status,  # Include status if response was received before exception
            },
        )
