from __future__ import annotations as _annotations
from pathlib import Path
from fastapi.responses import StreamingResponse
from fastapi import HTTPException, Depends
from typing import AsyncGenerator, Union
from fastapi import Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import fastapi
import json
from pydantic import BaseModel
from typing import List
from datetime import datetime
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPart,
    UserPromptPart,
    ModelMessage,
    TextPart,
    ModelRequest,
    ModelResponse,
)
from sqlmodel import Session
from contextlib import asynccontextmanager
from pydantic_ai import Agent
import os

from helpers.Manager import agent
from helpers.models import create_db_and_tables, get_session, User, Conversation, Message as DBMessage


THIS_DIR = Path(__file__).parent
# Create an instance of your tools

PRISM_COMPONENTS_DIR = Path("./node_modules/prismjs/components")  # Relative
# Validate that the directory exists when the app starts.  Important!
if not PRISM_COMPONENTS_DIR.is_dir():
    raise ValueError(f"Prism components directory not found: {PRISM_COMPONENTS_DIR}")


async def gemini(prompt: str) -> str:
    """
    Simple function that takes a prompt and returns a Gemini response.
    
    Args:
        prompt: The text prompt to send to Gemini
        
    Returns:
        The text response from Gemini
    """
    model = GeminiModel(
    "gemini-2.0-flash", provider=GoogleGLAProvider(api_key=os.getenv("GEMINI_API_KEY"))
    )

    agent = Agent(model=model,
                  system_prompt="Based on the user's prompt, generate a title for the conversation. The title should be a single sentence that captures the essence of the conversation. The title should be no more than 10 words."
                  )
    response = await agent.run(prompt)
    print(response, "\n")
    return response.data






@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    # Initialize database on startup
    create_db_and_tables()
    yield
    # Clean up resources if needed


app = fastapi.FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow your frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

class ChatMessage(BaseModel):
    role: str
    parts: List[Part]


class Part(BaseModel):
    type: str
    content: str


class AgentStreamEvent(BaseModel):
    type: str
    data: Union[PartStartEvent, PartDeltaEvent, FunctionToolCallEvent, FunctionToolResultEvent, FinalResultEvent]

def event_to_json_string(event):
    """Convert event objects to JSON string."""
    event_type = 'part_start'
    if isinstance(event, PartDeltaEvent):
        event_type = 'part_delta'
    elif isinstance(event, FunctionToolCallEvent):
        event_type = 'tool_call'
    elif isinstance(event, FunctionToolResultEvent):
        event_type = 'tool_result'
        
    event_dict = {
        'type': event_type,
        'data': event_to_dict(event)
    }
    return json.dumps(event_dict)

def event_from_json_string(json_str):
    """Convert JSON string back to event object."""
    data = json.loads(json_str)
    event_data = data['data']
    
    if data['type'] == 'part_start':
        return PartStartEvent(
            index=event_data["index"],
            part=TextPart(
                content=event_data["part"]["content"],
                part_kind=event_data["part"]["part_kind"]
            ) if event_data.get("part") else None,
            event_kind=event_data["event_kind"]
        )
    elif data['type'] == 'part_delta':
        return PartDeltaEvent(
            index=event_data["index"],
            delta=TextPartDelta(
                content_delta=event_data["delta"]["content"],
                part_delta_kind=event_data["delta"]["part_kind"]
            ) if event_data.get("delta") else None,
            event_kind=event_data["event_kind"]
        )
    elif data['type'] == 'tool_call':
        return FunctionToolCallEvent(
            part=ToolCallPart(
                tool_name=event_data["tool_call"]["name"],
                args=event_data["tool_call"]["args"],
                tool_call_id=event_data["tool_call"]["tool_call_id"]
            ),
            call_id=event_data["call_id"],
            event_kind=event_data["event_kind"]
        )
    elif data['type'] == 'tool_result':
        return FunctionToolResultEvent(
            result=ToolResult(
                tool_name=event_data["tool_result"]["name"],
                content=event_data["tool_result"]["content"],
                tool_call_id=event_data["tool_result"]["tool_call_id"],
                timestamp=datetime.fromisoformat(event_data["tool_result"]["timestamp"])
            ),
            tool_call_id=event_data["tool_call_id"],
            event_kind=event_data["event_kind"]
        )
    return None

def event_to_dict(event):
    """Convert event objects to serializable dictionaries."""
    if isinstance(event, PartStartEvent):
        return {
            "index": event.index,
            "part": {
                "content": event.part.content,
                "part_kind": event.part.part_kind
            } if event.part else None,
            "event_kind": event.event_kind
        }
    elif isinstance(event, PartDeltaEvent):
        return {
            "index": event.index,
            "delta": {
                "content": event.delta.content_delta,
                "part_kind": event.delta.part_delta_kind
            } if event.delta else None,
            "event_kind": event.event_kind
        }
    elif isinstance(event, FunctionToolCallEvent):
        return {
            "tool_call": {
                "name": event.part.tool_name,
                "args": event.part.args,
                "tool_call_id": event.part.tool_call_id
            },
            "call_id": event.call_id,
            "event_kind": event.event_kind
        }
    elif isinstance(event, FunctionToolResultEvent):
        return {
            "tool_result": {    
                "name": event.result.tool_name,
                "content": event.result.content,
                "tool_call_id": event.result.tool_call_id,
                "timestamp": event.result.timestamp.isoformat()
            },
            "tool_call_id": event.tool_call_id,
            "event_kind": event.event_kind
        }
    return vars(event)

def model_message_to_dict(message: Union[ModelRequest, ModelResponse]) -> dict:
    """Convert a ModelRequest or ModelResponse to a dictionary for storage"""
    if isinstance(message, ModelRequest):
        return {
            "type": "model_request",
            "parts": [
                {
                    "type": part.__class__.__name__,
                    "content": (
                        {
                            "name": part.tool_name,
                            "args": part.args,
                            "tool_call_id": part.tool_call_id
                        }
                        if isinstance(part, ToolCallPart)
                        else part.content
                    ),
                    "part_kind": part.part_kind if hasattr(part, 'part_kind') else "text",
                }
                for part in message.parts
            ],
            "kind": message.kind
        }
    else:  # ModelResponse
        return {
            "type": "model_response",
            "parts": [
                {
                    "type": part.__class__.__name__,
                    "content": (
                        {
                            "name": part.tool_name,
                            "args": part.args,
                            "tool_call_id": part.tool_call_id
                        }
                        if isinstance(part, ToolCallPart)
                        else part.content
                    ),
                    "part_kind": part.part_kind if hasattr(part, 'part_kind') else "text",
                }
                for part in message.parts
            ],
            "model_name": message.model_name,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "kind": message.kind
        }

def dict_to_model_message(data: dict) -> Union[ModelRequest, ModelResponse]:
    """Convert a stored dictionary back to a ModelRequest or ModelResponse"""
    parts = []
    for part_data in data["parts"]:
        if part_data["type"] == "TextPart":
            parts.append(TextPart(
                content=part_data["content"],
                part_kind=part_data.get("part_kind", "text")
            ))
        elif part_data["type"] == "ToolCallPart":
            parts.append(ToolCallPart(
                tool_name=part_data["content"].get("name"),
                args=part_data["content"].get("args"),
                tool_call_id=part_data["content"].get("tool_call_id"),
                part_kind=part_data.get("part_kind", "text")
            ))
        elif part_data["type"] == "UserPromptPart":
            parts.append(UserPromptPart(
                content=part_data["content"],
                part_kind=part_data.get("part_kind", "text")
            ))
    
    if data["type"] == "model_request":
        return ModelRequest(
            parts=parts,
            kind=data.get("kind")
        )
    else:  # model_response
        return ModelResponse(
            parts=parts,
            model_name=data.get("model_name"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            kind=data.get("kind")
        )

def get_message_history(conversation: Conversation) -> List[ModelMessage]:
    """Convert stored conversation messages into a list of ModelMessages for the model"""
    message_history = []
    
    # Sort messages by creation time to maintain order
    sorted_messages = sorted(conversation.messages, key=lambda m: m.created_at)
    
    for message in sorted_messages:
        try:
            # Parse the JSON string stored in message content
            message_data = json.loads(message.content)
            model_message = dict_to_model_message(message_data)
            message_history.append(model_message)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error processing message {message.id}: {str(e)}")
            continue
            
    return message_history

@app.post("/chat")
async def chat(prompt: str, conversation_id: str, session: Session = Depends(get_session)):
    """
    Endpoint to initiate a chat session and stream the response.
    
    """
    # Get or create conversation
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        conversation = Conversation(
            id=conversation_id,
            title=await gemini(prompt),  # Generate title using Gemini
            user_id=1  # You might want to get this from auth context
        )
        session.add(conversation)
        session.commit()

    # Get message history from the conversation
    message_history = get_message_history(conversation)

    
    
    async def generate_chunks() -> AsyncGenerator[str, None]:  # Changed return type to str since we're yielding JSON strings
        async with agent.iter(user_prompt=prompt, message_history=message_history) as run:
            async for node in run:
                if agent.is_user_prompt_node(node):
                    print("here",node.request, "\n")
                elif agent.is_model_request_node(node):
                    # A model request node => We can stream tokens from the model's request

                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart):
                                    yield "data: " + event_to_json_string(event) + "\n\n"
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    yield "data: " + event_to_json_string(event) + "\n\n"
                                # elif isinstance(event.delta, ToolCallPartDelta):
                                #     print(event, "\n")
                     # Save the complete message
                    db_message = DBMessage(
                        content=json.dumps(model_message_to_dict(node.request)),
                        is_user_message=False,
                        conversation_id=conversation_id
                    )
                    session.add(db_message)
                    session.commit()
                elif agent.is_call_tools_node(node):
                    # A handle-response node => The model returned some data, potentially calls a tool
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            # print("tool call", event)
                            yield "data: " + event_to_json_string(event) + "\n\n"
                    db_message = DBMessage(
                        content=json.dumps(model_message_to_dict(node.model_response)),
                        is_user_message=False,
                        conversation_id=conversation_id
                    )

                    session.add(db_message)
                    session.commit()
                    # print(node.model_response, "\n")
                # elif Agent.is_end_node(node):
                #     assert run.result.data == node.data.data
                #     # Once an End node is reached, the agent run is complete
                #     print(run.result, "\n")
    
    return StreamingResponse(
        generate_chunks(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


@app.get("/api/prism-language/")
async def get_prism_language(
    name: str = Query(
        ...,
        title="Language Name",
        description="The name of the Prism.js language component to retrieve.",
    ),
):
    """
    Serves Prism.js language components.  Only serves minified .min.js files
    from a specified directory, preventing path traversal vulnerabilities.
    Expects the language name as a query parameter (e.g., ?name=python).
    """

    # Sanitize the language name:  prevent path traversal attacks
    safe_language_name = name.replace("..", "")  # Remove ".."
    safe_language_name = safe_language_name.strip("/")

    # print("hi there", safe_language_name)  # Remove leading/trailing slashes

    filename = f"prism-{safe_language_name}.min.js"
    filepath = PRISM_COMPONENTS_DIR / filename

    # Security check: Verify the file exists *and* is within the allowed directory
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Language '{name}' not found")

    # Double check (more robust)
    try:
        filepath = filepath.resolve(
            strict=True
        )  # Raise error if the file doesn't exist or is a broken symlink
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Language '{name}' not found")

    if not str(filepath).startswith(
        str(PRISM_COMPONENTS_DIR.resolve())
    ):  # More robust check
        raise HTTPException(
            status_code=403, detail="Access denied:  File is outside allowed directory"
        )

    # Serve the file
    return FileResponse(
        filepath, media_type="application/javascript"
    )  # Correct media ty


# Define request models for API endpoints
class UserCreate(BaseModel):
    email: str
    name: str = None

class ConversationCreate(BaseModel):
    title: str
    user_id: int

class MessageCreate(BaseModel):
    content: str
    is_user_message: bool = True
    conversation_id: int

# Database API endpoints
@app.post("/users/", response_model=dict)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = User(email=user.email, name=user.name)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return {"status": "success", "user": db_user}

@app.get("/users/{user_id}", response_model=dict)
def read_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "user": user}

@app.post("/conversations/", response_model=dict)
def create_conversation(conversation: ConversationCreate, session: Session = Depends(get_session)):
    user = session.get(User, conversation.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_conversation = Conversation(title=conversation.title, user_id=conversation.user_id)
    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)
    return {"status": "success", "conversation": db_conversation}

@app.get("/conversations/{conversation_id}", response_model=dict)
def read_conversation(conversation_id: str, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "conversation": conversation}

@app.get("/users/{user_id}/conversations", response_model=dict)
def read_user_conversations(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "conversations": user.conversations}

@app.post("/messages/", response_model=dict)
def create_message(message: MessageCreate, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db_message = DBMessage(
        content=message.content,
        is_user_message=message.is_user_message,
        conversation_id=message.conversation_id
    )
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return {"status": "success", "message": db_message}

@app.get("/conversations/{conversation_id}/messages", response_model=dict)
def read_conversation_messages(conversation_id: str, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "messages": conversation.messages}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)