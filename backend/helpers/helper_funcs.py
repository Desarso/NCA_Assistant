from custom.models.gemini import GeminiModel
from custom.providers.google_gla import GoogleGLAProvider
from custom import Agent
import os

async def gemini(prompt: str) -> str:
    """
    Simple function that takes a prompt and returns a Gemini response.

    Args:
        prompt: The text prompt to send to Gemini

    Returns:
        The text response from Gemini
    """
    model = GeminiModel(
        "gemini-2.0-flash",
        provider=GoogleGLAProvider(api_key=os.getenv("GEMINI_API_KEY")),
    )

    agent = Agent(
        model=model,
        system_prompt="Based on the user's prompt, generate a title for the conversation. The title should be a single sentence that captures the essence of the conversation. The title should be no more than 10 words.",
    )
    response = await agent.run(prompt)
    # print(response, "\n")
    return response.data
