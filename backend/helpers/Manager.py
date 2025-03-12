from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
import os
import logging
# from pydantic_ai import agent_tool # Assuming you'll use agent_tool later, but not crucial for this core logic.
from dotenv import load_dotenv
import time
import threading
import requests
import json
from typing import Tuple, Optional, Dict, Any, List
import sys
import subprocess
import tempfile
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

tenant_id = os.getenv("TENANT_ID")
client_id = os.getenv("APP_ID")
client_secret = os.getenv("SECRET")

model = GeminiModel(
    "gemini-2.0-flash", provider=GoogleGLAProvider(api_key=os.getenv("GEMINI_API_KEY"))
)
# Create an agent with your tools
agent = Agent(
    model=model,
system_prompt="""
Okay, here's a prompt designed to guide your IT agent, emphasizing caution, confirmation, and diligent performance:

**Prompt for IT Agent:**

"You are an expert IT Administrator with access to powerful Microsoft Graph API tools. Your primary goal is to efficiently manage users, teams, and channels within our Microsoft Azure AD environment based on user requests.  Before executing any task, understand the request's implications thoroughly.

**Important Guidelines:**

*   **Prioritize Confirmation:** BEFORE performing any action that deletes data (deleting users, deleting teams, deleting channels), ALWAYS confirm with the user (via a message stating clearly what the action is and how it is permanent) that they intend to proceed.  WAIT FOR EXPLICIT APPROVAL before executing the command. If you do not receive explict approval the user should have the opportunity to cancel the request. If the user wants to cancel the request tell the user that the process has been terminated.

*   **Security and Data Loss Prevention:** Be EXTREMELY cautious with commands that modify user permissions, team memberships, or delete data. Always double-check the target user/team/channel ID before execution. NEVER perform actions that could unintentionally grant excessive permissions or lead to data loss.
*   **Error Handling:** If you encounter an error, log the full error message, including any API details provided. Report the error to the user with a clear explanation of what went wrong and potential next steps. Do not proceed with subsequent actions until the initial error is resolved.
*   **Logging and Audit Trail:** Every action you take MUST be logged. The logging is handled by the underlying GraphManager tools, but be aware of the importance of maintaining an accurate audit trail.
*   **Understand Tools thoroughly:** Study and comprehend the functionalities and parameters of each available tool. Understanding the tool's capabilities is essential to executing tasks accurately and minimizing potential errors.
*   **Be clear:** When generating information to the user you should ensure that the information is easily understood and precise.

**Available Tools:**

You have access to the following tools provided by the `GraphManager` class:

*   `create_user`: Creates a new user.
*   `list_users`: Lists all users.
*   `create_team`: Creates a new team.
*   `add_user_to_team`: Adds a user to a team.
*   `list_teams`: Lists all teams.
*   `list_team_members`: Lists members of a team.
*   `search_users`: Searches for users.
*   `get_user`: Gets details for a specific user.
*   `update_user`: Updates a user's properties.
*   `delete_user`: Deletes a user.
*   `delete_team`: Deletes a team.
*   `search_teams`: Searches for teams.
*   `create_channel`: Creates a new channel.
*   `list_channels`: Lists channels within a team.
*   `delete_channel`: Deletes a channel.
*   `python_interpreter`: Executes Python code.
*   `duckduckgo_search`: Searches the web.

**Workflow:**

1.  **Receive Request:** A user will provide a natural language request related to user, team, or channel management.
2.  **Parse and Understand:** Carefully analyze the request to fully understand the user's intent and required actions.
3.  **Plan Execution:** Develop a clear plan of the steps necessary to fulfill the request using the available tools.
4.  **Confirmation (For Deletion Actions):** If the plan involves deleting any resource, ALWAYS confirm with the user FIRST.
5.  **Tool Execution:** Execute the tools in the planned sequence, carefully providing the correct parameters.
6.  **Error Handling:** Monitor for errors during tool execution. Handle errors gracefully and inform the user.
7.  **Provide Feedback:**  Provide the user with clear and concise feedback on the successful completion of the request, or a detailed explanation of any errors encountered.

**Example Scenario:**

**User Request:** "Please delete user John.Doe@example.com."

**Your Actions:**

1.  **Parse and Understand:** The user wants to delete a user with the email John.Doe@example.com.
2.  **Confirmation:** Send the following message to the user: "You have requested to permanently delete user John.Doe@example.com. This action cannot be undone and all associated data will be removed. Do you wish to proceed with this action? [Yes/No]"
3.  **Wait for Explicit Approval:** Wait for the user to respond with "Yes" or "No".
4.  **If "Yes":** Execute the `delete_user` tool with the user ID "John.Doe@example.com".
5.  **If "No":** Send the user a message that the process has been terminated and inform the user that no process has been initiated.
6.  **Provide Feedback:** If the user is deleted send a message that "User John.Doe@example.com has been deleted successfully." If the user is not deleted, inform the user that no changes were made and all processes has been terminated.
7.  **Error Handling:** If any error has occurred, inform the user immediately and clearly the nature of the error that occurred.

**You are evaluated on accuracy, thoroughness, caution, and clear communication. Strive to be a reliable and trustworthy IT administrator."**

"""
,tools=[duckduckgo_search_tool()],
)


# Initialize logging (optional, but recommended)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables to hold token information.  These need to exist
# outside the class/function to maintain their state
_token = None
_headers = {}
_token_expiry = None
_token_lock = threading.Lock()


def refresh_token() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
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


def _make_request(method: str, url: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
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


## ✅ 1. Create a user
@agent.tool
def create_user(ctx: RunContext, display_name:str, user_principal_name:str, password:str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Creates a new user in Microsoft Azure AD.

    Args:
        display_name (str): The display name for the new user
        user_principal_name (str): The user principal name (email format) for the new user
        password (str): The initial password for the new user

    Returns:
        tuple: (response_data, error) where response_data contains the created user details if successful,
        or None and error details if failed
    """
    url = "https://graph.microsoft.com/v1.0/users"
    payload = {
        "accountEnabled": True,
        "displayName": display_name,
        "mailNickname": user_principal_name.split('@')[0],
        "userPrincipalName": user_principal_name,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": password
        }
    }
    response, error = _make_request("POST", url, json_data=payload)
    if error:
        logging.error(f"Failed to create user: {error}")
        return None, error

    logging.info(f"User '{display_name}' created successfully with ID {response.get('id')}")
    return response, None

## ✅ 2. List all users
@agent.tool
def list_users(ctx: RunContext) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Lists all users in Microsoft Azure AD.

    Returns:
        tuple: (users_list, error) where users_list contains all users if successful,
        or None and error details if failed
    """
    url = "https://graph.microsoft.com/v1.0/users"
    all_users = []

    try:
        while url:
            response, error = _make_request("GET", url)
            print("response", response)

            if error:
                logging.error(f"Failed to list users: {error}")
                return None, error

            users = response.get('value', [])
            all_users.extend(users)
            url = response.get('@odata.nextLink')

        logging.info(f"Successfully retrieved {len(all_users)} users")
        return all_users, None

    except Exception as e:
        logging.exception(f"Error listing users: {e}")
        return None, {"error": "Unexpected error listing users", "details": str(e)}

## ✅ 3. Create a team
@agent.tool
def create_team(ctx: RunContext, team_name:str, description:str, owner_email:str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Creates a new team in Microsoft Teams.

    Args:
        team_name (str): The display name for the new team
        description (str): The description for the new team
        owner_email (str): The email address of the user who will be the team owner

    Returns:
        tuple: (response_data, error) where response_data contains the created team details if successful,
        or None and error details if failed
    """
    url = "https://graph.microsoft.com/v1.0/teams"
    payload = {
        "template@odata.bind": "https://graph.microsoft.com/v1.0/teamsTemplates('standard')",
        "displayName": team_name,
        "description": description,
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{owner_email}')"
            }
        ]
    }

    response, error = _make_request("POST", url, json_data=payload)
    if error:
        logging.error(f"Failed to create team: {error}")
        return None, error

    logging.info(f"Team '{team_name}' created successfully with ID {response.get('id')}")
    return response, None


## ✅ 4. Add a user to a team
@agent.tool
def add_user_to_team(ctx: RunContext, team_id:str, user_email:str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Adds a user to an existing Microsoft Team.

    Args:
        team_id (str): The ID of the team to add the user to
        user_email (str): The email address of the user to add

    Returns:
        tuple: (response_data, error) where response_data contains the member addition details if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/members"
    payload = {
        "@odata.type": "#microsoft.graph.aadUserConversationMember",
        "roles": [],
        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_email}')"
    }

    response, error = _make_request("POST", url, json_data=payload)

    if error:
        logging.error(f"Failed to add user to team: {error}")
        return None, error

    logging.info(f"User '{user_email}' added to team {team_id} with member ID {response.get('id')}")
    return response, None

## ✅ 5. List all teams
@agent.tool
def list_teams(ctx: RunContext) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Lists all teams in Microsoft Teams.

    Returns:
        tuple: (teams_list, error) where teams_list contains all teams if successful,
        or None and error details if failed
    """
    url = "https://graph.microsoft.com/v1.0/teams"
    all_teams = []
    try:
        while url:
            response, error = _make_request("GET", url)

            if error:
                logging.error(f"Failed to list teams: {error}")
                return None, error

            teams = response.get('value', [])
            all_teams.extend(teams)
            url = response.get('@odata.nextLink')

        logging.info(f"Successfully retrieved {len(all_teams)} teams")
        return all_teams, None
    except Exception as e:
        logging.exception(f"Error listing teams: {e}")
        return None, {"error": "Unexpected error listing teams", "details": str(e)}

## ✅ 6. List all members of a specific Microsoft Team
@agent.tool
def list_team_members(ctx: RunContext, team_id:str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Lists all members of a specific Microsoft Team.

    Args:
        team_id (str): The ID of the team to list members from

    Returns:
        tuple: (members_list, error) where members_list contains all team members if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/members"
    all_members = []
    try:
        while url:
            response, error = _make_request("GET", url)

            if error:
                logging.error(f"Failed to list team members: {error}")
                return None, error

            members = response.get('value', [])
            all_members.extend(members)
            url = response.get('@odata.nextLink')

        logging.info(f"Successfully retrieved {len(all_members)} members from team {team_id}")
        return all_members, None
    except Exception as e:
        logging.exception(f"Error listing team members: {e}")
        return None, {"error": "Unexpected error listing team members", "details": str(e)}

## ✅ 7. Search for users
@agent.tool
def search_users(ctx: RunContext, search_string:str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Searches for users whose display name contains the search string.

    Args:
        search_string (str): The string to search for in user properties

    Returns:
        tuple: (users_list, error) where users_list contains matching users if successful,
        or None and error details if failed
    """
    # Matches "Manager", "Senior Manager", "Manager, Sales"
    url = f"https://graph.microsoft.com/v1.0/users?$filter=startsWith(displayName, '{search_string}')"
    all_users = []
    try:
        while url:
            response, error = _make_request("GET", url)

            if error:
                logging.error(f"Failed to search users: {error}")
                return None, error

            users = response.get('value', [])
            all_users.extend(users)
            url = response.get('@odata.nextLink')

        logging.info(f"Found {len(all_users)} users matching '{search_string}' in field 'displayName'")
        return all_users, None
    except Exception as e:
        logging.exception(f"Error searching users: {e}")
        return None, {"error": "Unexpected error searching users", "details": str(e)}

@agent.tool
def search_users_by_field(ctx: RunContext, search_string: str, filter_field: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Searches for users whose display name contains the search string.
    
    Args:
        search_string (str): The string to search for in user properties
        filter_field (str, optional): 
            - displayName: The name displayed in the address book, default to this if not specified
            - givenName: The user's first name
            - surname: The user's last name 
            - mail: The user's email address
            - userPrincipalName: The principal name used to sign in
            - jobTitle: The user's job title
            - mobilePhone: The user's mobile phone number
            - officeLocation: The user's office location
        
    Returns:
        tuple: (users_list, error) where users_list contains matching users if successful,
        or None and error details if failed
    """
    all_users = []
    url = "https://graph.microsoft.com/v1.0/users"
    
    # Continue fetching pages until no more nextLink
    while url:
        response, error = _make_request("GET", url)
        
        if error:
            logging.error(f"Failed to search users: {error}")
            return None, error
        
        if response:
            users = response.get('value', [])
            all_users.extend(users)
            
            # Get the URL for the next page, if any
            url = response.get('@odata.nextLink')
        else:
            url = None
    
    # Filter users after collecting all pages
    filtered_users = [user for user in all_users if search_string.lower() in str(user.get(filter_field, '')).lower()]
    logging.info(f"Found {len(filtered_users)} users matching '{search_string}' in field '{filter_field}'")
    
    return filtered_users, None
## ✅ 8. Get details for a specific user by their ID or userPrincipalName.
@agent.tool
def get_user(ctx: RunContext, user_id:str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Gets details for a specific user by their ID or userPrincipalName.

    Args:
        user_id (str): The user's ID or userPrincipalName

    Returns:
        tuple: (user_data, error) where user_data contains the user details if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    response, error = _make_request("GET", url)

    if error:
        logging.error(f"Failed to get user: {error}")
        return None, error

    logging.info(f"Successfully retrieved details for user {response.get('displayName')} ({user_id})")
    return response, None

#make tools for update user display name, job title, and email all separate tools
@agent.tool
def update_user_display_name(ctx: RunContext, user_id: str, display_name: str) -> Tuple[None, Optional[Dict[str, Any]]]:
    """Updates a user's display name.

    Args:
        user_id (str): The user's ID or userPrincipalName
        display_name (str): The new display name for the user

    Returns:
        tuple: (None, error) where error is None if successful or contains error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    updates = {"displayName": display_name}

    response, error = _make_request("PATCH", url, json_data=updates)

    if error:
        logging.error(f"Failed to update user display name: {error}")
        return None, error

    logging.info(f"Display name for user '{user_id}' updated successfully to '{display_name}'")
    return None, None

@agent.tool
def update_user_job_title(ctx: RunContext, user_id: str, job_title: str) -> Tuple[None, Optional[Dict[str, Any]]]:
    """Updates a user's job title.

    Args:
        user_id (str): The user's ID or userPrincipalName
        job_title (str): The new job title for the user

    Returns:
        tuple: (None, error) where error is None if successful or contains error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    updates = {"jobTitle": job_title}

    response, error = _make_request("PATCH", url, json_data=updates)

    if error:
        logging.error(f"Failed to update user job title: {error}")
        return None, error

    logging.info(f"Job title for user '{user_id}' updated successfully to '{job_title}'")
    return None, None

@agent.tool
def update_user_email(ctx: RunContext, user_id: str, email: str) -> Tuple[None, Optional[Dict[str, Any]]]:
    """Updates a user's email address.

    Args:
        user_id (str): The user's ID or userPrincipalName
        email (str): The new email address for the user

    Returns:
        tuple: (None, error) where error is None if successful or contains error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    updates = {"mail": email, "userPrincipalName": email}

    response, error = _make_request("PATCH", url, json_data=updates)

    if error:
        logging.error(f"Failed to update user email: {error}")
        return None, error

    logging.info(f"Email for user '{user_id}' updated successfully to '{email}'")
    return None, None


## ✅ 10. Delete a user
@agent.tool
def delete_user(ctx: RunContext, user_id:str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Deletes a user from Microsoft Azure AD.

    Args:
        user_id (str): The user's ID or userPrincipalName

    Returns:
        tuple: (success_message, error) where success_message indicates successful deletion
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    response, error = _make_request("DELETE", url)

    if error:
        logging.error(f"Failed to delete user: {error}")
        return None, error

    logging.info(f"User '{user_id}' deleted successfully")
    return f"Successfully deleted user {user_id}", None  # Return success message

## ✅ 11. Delete a Microsoft Team
@agent.tool
def delete_team(ctx: RunContext, team_id:str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Deletes a Microsoft Team.

    Args:
        team_id (str): The ID of the team to delete

    Returns:
        tuple: (success_message, error) where success_message indicates successful deletion
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}"
    response, error = _make_request("DELETE", url)

    if error:
        logging.error(f"Failed to delete team: {error}")
        return None, error

    logging.info(f"Team '{team_id}' deleted successfully")
    return f"Successfully deleted team {team_id}", None  # Return success message

## ✅ 12. Search for teams
@agent.tool
def search_teams(ctx: RunContext, search_string:str, filter_field:str = "displayName") -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Searches for teams whose display name contains the search string.

    Args:
        search_string (str): The string to search for in team names
        filter_field (str, optional): The field to search in. Defaults to "displayName"

    Returns:
        tuple: (teams_list, error) where teams_list contains matching teams if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams?$filter=contains({filter_field}, '{search_string}')"
    all_teams = []
    try:
        while url:
            response, error = _make_request("GET", url)

            if error:
                logging.error(f"Failed to search teams: {error}")
                return None, error

            teams = response.get('value', [])
            all_teams.extend(teams)
            url = response.get('@odata.nextLink')

        logging.info(f"Found {len(all_teams)} teams matching '{search_string}' in field '{filter_field}'")
        return all_teams, None
    except Exception as e:
        logging.exception(f"Error searching teams: {e}")
        return None, {"error": "Unexpected error searching teams", "details": str(e)}

## ✅ 13. Create a standard channel
@agent.tool
def create_standard_channel(ctx: RunContext, team_id:str, channel_name:str, description:str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Creates a new standard channel within a Microsoft Team.

    Args:
        team_id (str): The ID of the team
        channel_name (str): The display name of the channel
        description (str): A description for the channel

    Returns:
        tuple: (response_data, error) where response_data contains the created channel details if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
    payload = {
        "displayName": channel_name,
        "description": description
    }

    response, error = _make_request("POST", url, json_data=payload)

    if error:
        logging.error(f"Failed to create channel: {error}")
        return None, error

    logging.info(f"Channel '{channel_name}' created successfully in team '{team_id}' with ID {response.get('id')}")
    return response, None

## ✅ 13b. Create a private channel
@agent.tool
def create_private_channel(ctx: RunContext, team_id:str, channel_name:str, description:str, owners:List[str]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Creates a new private channel within a Microsoft Team.

    Args:
        team_id (str): The ID of the team
        channel_name (str): The display name of the channel
        description (str): A description for the channel
        owners (list): A list of user IDs who should be owners of the private channel

    Returns:
        tuple: (response_data, error) where response_data contains the created channel details if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
    payload = {
        "displayName": channel_name,
        "description": description,
        "membershipType": "private",
        "owners@odata.bind": [f"https://graph.microsoft.com/v1.0/users('{owner}')" for owner in owners]
    }

    response, error = _make_request("POST", url, json_data=payload)

    if error:
        logging.error(f"Failed to create private channel: {error}")
        return None, error

    logging.info(f"Private channel '{channel_name}' created successfully in team '{team_id}' with ID {response.get('id')} and {len(owners)} owners")
    return response, None

## ✅ 14. List all channels
@agent.tool
def list_channels(ctx: RunContext, team_id:str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """Lists all channels within a Microsoft Team.

    Args:
        team_id (str): The ID of the team to list channels from

    Returns:
        tuple: (channels_list, error) where channels_list contains all channels if successful,
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
    all_channels = []
    try:
        while url:
            response, error = _make_request("GET", url)

            if error:
                logging.error(f"Failed to list channels: {error}")
                return None, error

            channels = response.get('value', [])
            all_channels.extend(channels)
            url = response.get('@odata.nextLink')

        logging.info(f"Successfully retrieved {len(all_channels)} channels from team {team_id}")
        return all_channels, None
    except Exception as e:
        logging.exception(f"Error listing channels: {e}")
        return None, {"error": "Unexpected error listing channels", "details": str(e)}

## ✅ 15. Delete a channel
@agent.tool
def delete_channel(ctx: RunContext, team_id:str, channel_id:str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Deletes a channel from a Microsoft Team.

    Args:
        team_id (str): The ID of the team containing the channel
        channel_id (str): The ID of the channel to delete

    Returns:
        tuple: (success_message, error) where success_message indicates successful deletion
        or None and error details if failed
    """
    url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}"
    response, error = _make_request("DELETE", url)
    

    if error:
        logging.error(f"Failed to delete channel: {error}")
        return None, error

    logging.info(f"Channel '{channel_id}' deleted successfully from team '{team_id}'")
    return f"Successfully deleted channel {channel_id} from team {team_id}", None  # Return success message


## ✅ 16. List joined teams
@agent.tool
def list_user_joined_teams(ctx: RunContext, user_id: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """
    Retrieves the list of Microsoft Teams that a user has joined.

    Args:
        ctx (RunContext): The context object containing authentication and configuration details.
        user_id (str): The user's ID or userPrincipalName.

    Returns:
        tuple: A tuple containing:
            - A list of dictionaries, each representing a team the user has joined.
            - An error dictionary if an error occurred, or None if successful.
    """
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/joinedTeams"
    all_teams = []
    try:
        while url:
            response, error = _make_request("GET", url)

            if error:
                logging.error(f"Failed to get joined teams for user {user_id}: {error}")
                return None, error

            teams = response.get('value', [])
            all_teams.extend(teams)
            url = response.get('@odata.nextLink')

        logging.info(f"Successfully retrieved {len(all_teams)} joined teams for user {user_id}")
        return all_teams, None
    except Exception as e:
        logging.exception(f"Error getting joined teams: {e}")
        return None, {"error": "Unexpected error getting joined teams", "details": str(e)}


@agent.tool
def get_user_team_channel_memberships(ctx: RunContext, user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Retrieves all Microsoft Teams and Channels that a user is a member of.

    Args:
        user_id (str): The user's ID or userPrincipalName.

    Returns:
        tuple: A tuple containing:
            - A dictionary: { "teams": [team_details], "channels": {team_id: [channel_details]} }.
            - An error dictionary if an error occurred, or None if successful.
    """
    user_teams, teams_error = list_user_joined_teams(ctx, user_id)
    if teams_error:
        logging.error(f"Error getting teams for user {user_id}: {teams_error}")
        return None, teams_error

    user_channels = {}

    for team in user_teams:
        team_id = team['id']
        channels, channels_error = list_channels(ctx, team_id)
        if channels_error:
            logging.warning(f"Error getting channels for team {team_id}: {channels_error}")
            continue  # Proceed to the next team

        user_channels[team_id] = channels

    result = {"teams": user_teams, "channels": user_channels}
    logging.info(f"Found user {user_id} in {len(user_teams)} teams and retrieved channels for each.")
    return result, None



# add a python interpreter tool
@agent.tool
def python_interpreter(ctx: RunContext, code: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Executes Python code in a controlled environment.
    The python is an isolate enviroment with no internet access. Used mostly for math operations and getting the current date in a nice format.
    Please fetch the date in a readable format. aka "Month Day, Year"
    It is for executing logical operations. Do no use it for displaying information.
    Args:
        code (str): The Python code to execute.

    Returns:
        tuple: A tuple containing:
            - The output of the Python code.
            - An error dictionary if an error occurred, or None if successful.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, "script.py")
        
        try:
            # Write the code to a temporary file
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Create a new Python process with controlled environment
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30,  # Add timeout to prevent infinite loops
                env={
                    'PYTHONPATH': os.pathsep.join(sys.path),
                    'PATH': os.environ.get('PATH', ''),
                    'PYTHONIOENCODING': 'utf-8',
                }
            )
            
            if result.returncode != 0:
                return None, {
                    "error": "Code execution failed",
                    "details": result.stderr or "No error details available"
                }
            
            return result.stdout, None

        except subprocess.TimeoutExpired:
            return None, {
                "error": "Execution timeout",
                "details": "Code execution exceeded 30 second timeout"
            }
        except Exception as e:
            return None, {
                "error": "Execution error",
                "details": str(e)
            }




if __name__ == "__main__":
    print(search_users(None, "gabriel"))