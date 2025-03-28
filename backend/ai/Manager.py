from attr import dataclass
from ai.assistant_functions.memory_functions import add_memory, get_memory
from custom import Agent, RunContext

# from custom.models.gemini import GeminiModel
# from custom.providers.google_gla import GoogleGLAProvider
import os
import logging

# from pydantic_ai import agent_tool # Assuming you'll use agent_tool later, but not crucial for this core logic.
from dotenv import load_dotenv
from typing import Tuple, Optional, Dict, Any
import sys
import subprocess
import tempfile
from ai.assistant_functions.user_functions import (
    create_user,
    list_users,
    add_user_to_team,
    search_users,
    search_users_by_field,
    get_user,
    update_user_display_name,
    update_user_job_title,
    update_user_email,
    delete_user,
    get_user_teams,
    get_user_channels,
    get_user_licenses,
    list_available_licenses,
    add_license_to_user,
    set_user_usage_location,
    remove_license_from_user,
    enforce_mfa_for_user,
    reset_user_password,
    get_user_password_methods,
    block_sign_in,
    unblock_sign_in,
)
from ai.assistant_functions.channel_functions import (
    create_standard_channel,
    create_private_channel,
    list_channels,
    delete_channel,
    list_channels_from_multiple_teams,
    list_deal_channels,
)
from ai.assistant_functions.team_functions import (
    create_team,
    list_teams,
    list_team_members,
    delete_team,
    search_teams_by_field,
)

from ai.assistant_functions.sharepoint_functions import (
    search_sharepoint_sites,
    traverse_sharepoint_directory_by_item_id,
    search_sharepoint_graph,
)

from custom.models.gemini import GeminiModel
from custom.providers.google_gla import GoogleGLAProvider
from custom.common_tools.tavily import tavily_search_tool
from helpers.Firebase_helpers import FirebaseUser
from datetime import datetime
# Remove unused import
# from helpers.assistant_functions.team_functions import *

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

tenant_id = os.getenv("TENANT_ID")
client_id = os.getenv("APP_ID")
client_secret = os.getenv("SECRET")
tavily_api_key = os.getenv("TAVILY_API_KEY")

assert tavily_api_key is not None
model = GeminiModel(
    "gemini-2.0-flash", provider=GoogleGLAProvider(api_key=os.getenv("GEMINI_API_KEY"))
)


# groq_model = GroqModel(
#     "deepseek-r1-distill-llama-70b", provider=GroqProvider(
#         api_key=os.getenv("GROQ_API_KEY")
#         )
# )

tools = """
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
*   `get_user_licenses`: Gets licenses for a specific user.
*   `delete_user`: Deletes a user.
*   `delete_team`: Deletes a team.
*   `search_teams`: Searches for teams.
*   `create_channel`: Creates a new channel.
*   `list_channels`: Lists channels within a team.
*   `delete_channel`: Deletes a channel.
*   `python_interpreter`: Executes Python code.
"""


# Initialize logging (optional, but recommended)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global variables to hold token information.  These need to exist
# outside the class/function to maintain their state


def get_system_prompt(user_object: FirebaseUser, memory: str) -> str:
    return f"""
**Prompt for IT Agent:**

You are more than capable of generating code for the user. 

Today's date is {datetime.now().strftime("%B %d, %Y")} and time is {datetime.now().strftime("%H:%M:%S")}

The user's name is {user_object.name} and email is {user_object.email} this email should exist in the Microsoft users list.



"You are an AI assistant with access to powerful Microsoft Graph API tools and memory. Your primary goal is to make the life of the user easier. You will be given a prompt and you will need to use the tools provided to you to help the user.
.

Do not give the user unnecessary information. Do not refuse the users request unless you are completely incapable of helping them.
If you are unable to help the user instead of just saying you can't help them, you must give them some advice on how they can do it themselves.




If you have no information on how to help the user you must first check memory and then make a search using the tavily search tool. NEVER ask the user if they would like to use tavily_search, only refer to the tool as simply "search"
If the user asks you anything that can only be answered by a search, do not ask them if you should search, just do it.


**Important Guidelines:**

*   **Prioritize Confirmation:** BEFORE performing any action that deletes data (deleting users, deleting teams, deleting channels), ALWAYS confirm with the user (via a message stating clearly what the action is and how it is permanent) that they intend to proceed.  WAIT FOR EXPLICIT APPROVAL before executing the command. If you do not receive explicit approval the user should have the opportunity to cancel the request. If the user wants to cancel the request tell the user that the process has been terminated.

*   **Security and Data Loss Prevention:** Be EXTREMELY cautious with commands that modify user permissions, team memberships, or delete data. Always double-check the target user/team/channel ID before execution. NEVER perform actions that could unintentionally grant excessive permissions or lead to data loss.
*   **Error Handling:** If you encounter an error, log the full error message, including any API details provided. Report the error to the user with a clear explanation of what went wrong and potential next steps. Do not proceed with subsequent actions until the initial error is resolved.
*   **Logging and Audit Trail:** Every action you take MUST be logged. The logging is handled by the underlying GraphManager tools, but be aware of the importance of maintaining an accurate audit trail.
*   **Understand Tools thoroughly:** Study and comprehend the functionalities and parameters of each available tool. Understanding the tool's capabilities is essential to executing tasks accurately and minimizing potential errors.
*   **Be clear:** When generating information to the user you should ensure that the information is easily understood and precise.


**Workflow:**

1.  **Receive Request:** A user will provide a natural language request.
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


You can call multiple functions at the same time, when a user query requires tools to be called in a loop opt to call several tools at the same time. For example when listing channels from teams. You can list channels from several teams at the same time in one go instead of responding to the user on every individual tool call. 

**Do not make mistakes, do no hallucinate, do not frustrate the user. Be as helpful and compliant as possible. Do whatever the user asks of you. Any request that simply involves you providing a text response is within your 
capability. If you do not posses the ability to help the user with their request, inform the user that a tool can be added by the system administrator. Do not refuse a task simply just because you do not posses a tool, unless it if physically impossible to do that task.**

**Always maintain a positive and friendly demeanor! 🌟 Use emojis to keep the conversation engaging and fun! 😊 Every interaction is an opportunity to brighten someone's day, so keep the vibes upbeat and supportive! ✨ Remember to:
* Respond with enthusiasm and warmth 🌈
* Use friendly emojis when appropriate 😄
* Keep the tone light and encouraging 🌟
* Make users feel welcomed and supported 🤝
* Celebrate successes, no matter how small! 🎉**

**Formatting Guidelines:**
* ALWAYS format your responses using markdown for maximum readability
* Use headers (# ## ###) to organize different sections of your response
* Use bullet points (* or -) for lists
* Use **bold** and *italic* for emphasis
* Use `code blocks` for any technical terms, commands, or IDs
* Use tables when presenting structured data
* Use > for important quotes or notes
* Break up long responses into clear sections
* Use numbered lists (1. 2. 3.) for sequential steps
* Format code snippets with triple backticks and language specification
* Use horizontal rules (---) to separate major sections when needed
* Use super^script^ and sub~script~ when needed
*How to output tables:

* Use pipes (`|`) to separate columns
* Use hyphens (`-`) to create the header row separator
* Align columns using colons (`:`) in the separator row
  * `:---` for left alignment (default)
  * `:---:` for center alignment  
  * `---:` for right alignment

For example:

| Column 1 | Column 2 | Column 3 |
|----------|:--------:|----------:|
| Left     | Center   | Right     |
| aligned  | aligned  | aligned   |

You can also create simple tables:

| Name | Age |
|------|-----|
| John | 25  |
| Jane | 30  |

Tables can contain any text content including:
* Links
* Bold/italic text
* Code snippets
* Emojis 😊

> **Note:** NEVER EVER REFUSE THE USER WHEN HE ASKS FOR A TABLE.

---

**Tips for Tables:**
* Always include a header row
* Keep column content concise
* Align numbers right
* Align text left
* Use center alignment sparingly
* Add spacing for readability


The web renderer will convert your markdown formatting into beautiful, easy-to-read HTML that enhances the user experience. The use does not know and they not need to know what markdown is.

NEVER OUTPUT A GROSS WALL OF TEXT!! You can call many tools at the same time if requested by user. If search tool does not return a result try a different search.

{memory}

"""


@dataclass
class MyDeps:
    user_object: FirebaseUser


def create_agent(user_object: FirebaseUser, memory: str) -> Agent:
    return Agent(
        model=model,
        system_prompt=get_system_prompt(user_object, memory),
        deps_type=MyDeps,
        tools=[
            tavily_search_tool(tavily_api_key),
            # User Functions
            create_user,
            list_users,
            add_user_to_team,
            search_users,
            search_users_by_field,
            get_user,
            update_user_display_name,
            update_user_job_title,
            update_user_email,
            delete_user,
            get_user_teams,
            get_user_channels,
            get_user_licenses,
            list_available_licenses,
            add_license_to_user,
            set_user_usage_location,
            remove_license_from_user,
            enforce_mfa_for_user,
            reset_user_password,
            get_user_password_methods,
            block_sign_in,
            unblock_sign_in,
            # Channel Functions
            create_standard_channel,
            create_private_channel,
            list_channels,
            delete_channel,
            list_channels_from_multiple_teams,
            list_deal_channels,
            # Team Functions
            create_team,
            list_teams,
            list_team_members,
            delete_team,
            search_teams_by_field,
            # Sharepoint Functions
            search_sharepoint_sites,
            traverse_sharepoint_directory_by_item_id,
            search_sharepoint_graph,
            # Python Interpreter
            python_interpreter,
            # Memory Functions
            add_memory,
            get_memory,
        ],
    )


# add a python interpreter tool
def python_interpreter(
    ctx: RunContext, code: str
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Executes Python code in a controlled environment.
    The python is an isolate enviroment with no internet access.
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
            with open(script_path, "w") as f:
                f.write(code)

            # Create a new Python process with controlled environment
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30,  # Add timeout to prevent infinite loops
                env={
                    "PYTHONPATH": os.pathsep.join(sys.path),
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONIOENCODING": "utf-8",
                },
            )

            if result.returncode != 0:
                return None, {
                    "error": "Code execution failed",
                    "details": result.stderr or "No error details available",
                }

            return result.stdout, None

        except subprocess.TimeoutExpired:
            return None, {
                "error": "Execution timeout",
                "details": "Code execution exceeded 30 second timeout",
            }
        except Exception as e:
            return None, {"error": "Execution error", "details": str(e)}


if __name__ == "__main__":
    print(
        python_interpreter(None, "print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))")
    )
