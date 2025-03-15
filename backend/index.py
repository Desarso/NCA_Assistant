from __future__ import annotations as _annotations
from pathlib import Path
from fastapi.responses import StreamingResponse
from fastapi import HTTPException, Depends, Security
from typing import AsyncGenerator, Union
from fastapi import Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.openapi.docs import get_swagger_ui_html
import fastapi
import json
import firebase_admin
from firebase_admin import credentials, auth
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
    ToolReturnPart,
    RetryPromptPart,
)
from sqlmodel import Session
from contextlib import asynccontextmanager
from pydantic_ai import Agent
import os

from helpers.Manager import agent
from helpers.models import create_db_and_tables, get_session, User, Conversation, Message as DBMessage
from dotenv import load_dotenv

load_dotenv()



THIS_DIR = Path(__file__).parent
# Create an instance of your tools

PRISM_COMPONENTS_DIR = Path("./prismjs/components")  # Relative
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
    
    # Initialize Firebase Admin SDK if not already initialized
    if not firebase_admin._apps:
        from firebase.firebase_credentials import get_firebase_credentials
        cred = credentials.Certificate(get_firebase_credentials())
        firebase_admin.initialize_app(cred)
    
    yield
    # Clean up resources if needed


app = fastapi.FastAPI(
    lifespan=lifespan,
    title="Microsoft API Backend",
    description="API for Microsoft AI Services with Firebase authentication",
    version="1.0.0",
    docs_url=None,
    redoc_url=None
)

print(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],  # Get frontend URL from env
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Firebase auth bearer for API endpoints
security = HTTPBearer()

# OAuth2 password bearer for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class FirebaseUser:
    def __init__(self, uid: str, email: str, whitelisted: bool = False):
        self.uid = uid
        self.email = email
        self.whitelisted = whitelisted

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCredentials(BaseModel):
    email: str
    password: str


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> FirebaseUser:
    """
    Validate Firebase ID token and verify the user is whitelisted
    """
    try:
        # The token comes in the format "Bearer <token>"
        token = credentials.credentials
        # Verify the token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        
        # Get user claims to check if whitelisted
        uid = decoded_token['uid']
        user = auth.get_user(uid)
        
        # Check email
        email = user.email if user.email else decoded_token.get('email', '')
        
        # Get custom claims
        custom_claims = user.custom_claims or {}
        whitelisted = custom_claims.get('whitelisted', False)
        
        # Create user object
        firebase_user = FirebaseUser(uid=uid, email=email, whitelisted=whitelisted)
        
        # Check if the user is whitelisted
        if not firebase_user.whitelisted:
            raise HTTPException(
                status_code=403,
                detail="User is not authorized to access this resource. Contact administrator for whitelist access."
            )
            
        return firebase_user
        
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Firebase ID token has expired. Please sign in again.")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token. Please sign in again.")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Firebase ID token has been revoked. Please sign in again.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to validate Firebase ID token: {str(e)}")

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
        tool_result = event_data["tool_result"]
        if "content" in tool_result:
            return FunctionToolResultEvent(
                result=ToolReturnPart(
                    tool_name=tool_result["name"],
                    content=tool_result["content"],
                    tool_call_id=tool_result["tool_call_id"]
                ),
                tool_call_id=event_data["tool_call_id"],
                event_kind=event_data["event_kind"]
            )
        elif "retry_prompt" in tool_result:
            # Handle retry prompt case
            return FunctionToolResultEvent(
                result=RetryPromptPart(
                    content=tool_result["retry_prompt"],
                    tool_call_id=tool_result["tool_call_id"]
                ),
                tool_call_id=event_data["tool_call_id"],
                event_kind=event_data["event_kind"]
            )
        else:
            print(f"Unknown tool result format: {tool_result}")
            return None
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
async def chat(
    prompt: str, 
    conversation_id: str, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    """
    Endpoint to initiate a chat session and stream the response.
    
    """
    # Get or create conversation
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        # Check if user exists in the database, create if not
        user = session.get(User, current_user.uid)
        if not user:
            user = User(
                id=current_user.uid,
                email=current_user.email,
                name=current_user.email.split('@')[0] if current_user.email else None
            )
            session.add(user)
            session.commit()
            
        conversation = Conversation(
            id=conversation_id,
            title=await gemini(prompt),  # Generate title using Gemini
            user_id=current_user.uid
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
    current_user: FirebaseUser = Depends(get_current_user)
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
    user_id: str

class MessageCreate(BaseModel):
    content: str
    is_user_message: bool = True
    conversation_id: str


@app.get("/users/{user_id}", response_model=dict)
def read_user(
    user_id: str, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    # Users can only access their own information
    if user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own user data")
        
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "user": user}

@app.post("/conversations/", response_model=dict)
def create_conversation(
    conversation: ConversationCreate, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    # Users can only create conversations for themselves
    if conversation.user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Access denied: You can only create conversations for yourself")
        
    user = session.get(User, conversation.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_conversation = Conversation(title=conversation.title, user_id=conversation.user_id)
    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)
    return {"status": "success", "conversation": db_conversation}

@app.get("/conversations/{conversation_id}", response_model=dict)
def read_conversation(
    conversation_id: str, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Users can only access their own conversations
    if conversation.user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own conversations")
        
    return {"status": "success", "conversation": conversation}

@app.get("/users/{user_id}/conversations", response_model=dict)
def read_user_conversations(
    user_id: str, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    # Users can only access their own conversations
    if user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own conversations")
        
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "conversations": user.conversations}

@app.post("/messages/", response_model=dict)
def create_message(
    message: MessageCreate, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    conversation = session.get(Conversation, message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Users can only add messages to their own conversations
    if conversation.user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Access denied: You can only add messages to your own conversations")
    
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
def read_conversation_messages(
    conversation_id: str, 
    session: Session = Depends(get_session),
    current_user: FirebaseUser = Depends(get_current_user)
):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Users can only view messages from their own conversations
    if conversation.user_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Access denied: You can only view messages from your own conversations")
        
    return {"status": "success", "messages": conversation.messages}

# Custom Swagger UI routes
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
    )


@app.post("/auth/login", response_model=Token, tags=["authentication"])
async def login_for_access_token(credentials: UserCredentials):
    """
    Login with email/password to get a Firebase token for API access
    
    This endpoint is primarily for testing in Swagger UI.
    """
    try:
        # Sign in with Firebase Auth
        user = auth.get_user_by_email(credentials.email)
        
        # Create a custom token
        custom_token = auth.create_custom_token(user.uid)
        
        # In a real application, you would exchange this for an ID token
        # Here we're using it directly for simplicity in Swagger UI testing
        
        return {
            "access_token": custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/auth/token", response_model=Token, tags=["authentication"])
async def login_oauth(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token endpoint for Swagger UI
    """
    try:
        # Sign in with Firebase Auth
        user = auth.get_user_by_email(form_data.username)  # Using username field for email
        
        # Create a custom token
        custom_token = auth.create_custom_token(user.uid)
        
        return {
            "access_token": custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/auth/me", response_model=dict, tags=["authentication"])
async def get_current_user_info(current_user: FirebaseUser = Depends(get_current_user)):
    """
    Return information about the currently authenticated user
    """
    return {
        "status": "success",
        "user": {
            "uid": current_user.uid,
            "email": current_user.email,
            "whitelisted": current_user.whitelisted
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)