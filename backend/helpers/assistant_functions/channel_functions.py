
from pydantic_ai import RunContext
import logging
# from pydantic_ai import agent_tool # Assuming you'll use agent_tool later, but not crucial for this core logic.
from typing import Tuple, Optional, Dict, Any, List
from helpers.RequestHelper import make_request

## ✅ 13. Create a standard channel
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

    response, error = make_request("POST", url, json_data=payload)

    if error:
        logging.error(f"Failed to create channel: {error}")
        return None, error

    logging.info(f"Channel '{channel_name}' created successfully in team '{team_id}' with ID {response.get('id')}")
    return response, None

## ✅ 13b. Create a private channel
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

    response, error = make_request("POST", url, json_data=payload)

    if error:
        logging.error(f"Failed to create private channel: {error}")
        return None, error

    logging.info(f"Private channel '{channel_name}' created successfully in team '{team_id}' with ID {response.get('id')} and {len(owners)} owners")
    return response, None

## ✅ 14. List all channels
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
            response, error = make_request("GET", url)

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
    response, error = make_request("DELETE", url)
    

    if error:
        logging.error(f"Failed to delete channel: {error}")
        return None, error

    logging.info(f"Channel '{channel_id}' deleted successfully from team '{team_id}'")
    return f"Successfully deleted channel {channel_id} from team {team_id}", None  # Return success message


