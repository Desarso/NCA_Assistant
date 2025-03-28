from custom.tools import RunContext
from typing import Tuple
from mem0 import MemoryClient
from dotenv import load_dotenv
import os

load_dotenv()


client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))


def add_memory(ctx: RunContext[str], message: str) -> Tuple[str, str]:
    """Add a new memory to my persistent memory store.

    I use this function to store important information or experiences
    that I may need to reference later.

    Args:
        message: The content of the memory to be stored

    Returns:
        A tuple containing a success message and the stored memory content
    """
    message = [{"role": "user", "content": message}]
    client.add(message, user_id=ctx.deps.user_object.uid)
    return "Memory added successfully."

def get_memory(ctx: RunContext[str], query: str) -> Tuple[str, str]:
    """Retrieve memories from my persistent memory store based on a search query.

    I use this function to search through previously stored memories using a text query.
    Use this memory before using other search tools, to ensure you have the correct context. Avoid calling other tools first so as to not frustrate the user.


    Args:
        query: The search query to find relevant memories

    Returns:
        A tuple containing the search results and any associated metadata
    """
    results = client.search(query, user_id=ctx.deps.user_object.uid)
    return "Memory search completed successfully.", str(results)


def get_memory_no_context(user_id: str, query: str) -> Tuple[str, str]:
    """Retrieve memories from my persistent memory store based on a search query.

    I use this function to search through previously stored memories using a text query.
    Use this memory before using other search tools, to ensure you have the correct context. Avoid calling other tools first so as to not frustrate the user.

    Args:   
        user_id: The user ID to retrieve memories for
        query: The search query to find relevant memories

    Returns:
        A tuple containing the search results and any associated metadata
    """
    results = client.search(query, user_id=user_id)
    return "Memory from current question.", str(results)