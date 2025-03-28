from ai.assistant_functions.team_functions import search_teams_by_field
from custom import RunContext
import logging
import time
# from pydantic_ai import agent_tool # Assuming you'll use agent_tool later, but not crucial for this core logic.
from typing import Tuple, Optional, Dict, Any, List
from helpers.RequestHelper import make_request
from concurrent.futures import ThreadPoolExecutor, as_completed

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

## ✅ 16. List channels from multiple teams
def list_channels_from_multiple_teams(ctx: RunContext, team_ids: List[str], search_string: str = None, filter_field: str = "displayName") -> Tuple[Optional[Dict[str, List[Dict[str, Any]]]], Optional[Dict[str, Any]]]:
    """Lists all channels from multiple Microsoft Teams concurrently using multithreading.

    This function is useful when you need to list channels from multiple teams at once.
    Implements rate limiting to avoid hitting API limits.

    Args:
        team_ids (list): List of team IDs to list channels from
        search_string (str, optional): The string to search for in channel properties
        filter_field (str, optional): The field to search in. Defaults to "displayName"

    Returns:
        tuple: (teams_channels_dict, error) where teams_channels_dict contains a mapping of team IDs to their channels if successful,
        or None and error details if failed
    """
    teams_channels = {}
    # Reduce max workers to 5 to avoid rate limits
    max_workers = min(5, len(team_ids))
    
    def fetch_team_channels(team_id: str) -> Tuple[str, Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        # Add a small delay between requests to avoid rate limits
        time.sleep(0.5)
        channels, error = list_channels(ctx, team_id)
        return team_id, channels, error

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_team = {
                executor.submit(fetch_team_channels, team_id): team_id 
                for team_id in team_ids
            }
            
            # Process completed tasks
            for future in as_completed(future_to_team):
                team_id, channels, error = future.result()
                if error:
                    if isinstance(error, dict) and error.get('status_code') == 429:
                        logging.warning(f"Rate limit hit for team {team_id}, waiting before retrying...")
                        time.sleep(2)  # Wait 2 seconds on rate limit
                        # Retry once
                        channels, error = list_channels(ctx, team_id)
                        if error:
                            logging.error(f"Failed to list channels for team {team_id} after retry: {error}")
                            return None, error
                    else:
                        logging.error(f"Failed to list channels for team {team_id}: {error}")
                        return None, error
                teams_channels[team_id] = channels

        logging.info(f"Successfully retrieved channels from {len(team_ids)} teams using {max_workers} concurrent workers")
        return teams_channels, None
        
    except Exception as e:
        logging.exception(f"Unexpected error while fetching channels from multiple teams: {e}")
        return None, {"error": "Unexpected error while fetching channels from multiple teams", "details": str(e)}

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


def list_deal_channels(ctx: RunContext):
    """Lists all channels with 'deals' in their name in teams matching the 'NCA SF XXX' pattern."""

    # 1. Find all searcher teams using the naming pattern.
    teams, error = search_teams_by_field(ctx, filter_field='displayName', search_string='NCA SF')
    if error:
        print(f"Error searching for teams: {error}")
        return None, error

    searcher_team_ids = [team['id'] for team in teams if 'displayName' in team and team['displayName'].startswith('NCA SF')]

    # 2. List channels from multiple teams at once.
    if not searcher_team_ids:
        print("No searcher teams found.")
        return [], None

    all_channels, error = list_channels_from_multiple_teams(ctx, team_ids=searcher_team_ids)

    print("made it here", all_channels)

    if error:
        print(f"Error listing channels from multiple teams: {error}")
        return None, error

    # 3. Filter for channels with "deals" in their name (case-insensitive).
    deal_channels = []
    for team_id, channels in all_channels.items():
        for channel in channels:
            if 'displayName' in channel and 'deals' in channel['displayName'].lower():
                deal_channels.append({
                    'team_id': team_id,
                    'channel_id': channel['id'],
                    'channel_name': channel['displayName']
                })

    return deal_channels, None
