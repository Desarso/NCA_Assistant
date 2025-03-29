from datetime import datetime
import json
from typing import AsyncGenerator, List, Union
from fastapi import APIRouter, Depends, HTTPException, Request
from requests import Session

from ai.Manager import MyDeps, create_agent, get_system_prompt
from ai.assistant_functions.memory_functions import get_memory_no_context
from custom.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    ReasoningPart,
    ReasoningPartDelta,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from helpers.helper_funcs import gemini
from ai.models import get_session, User, Conversation, Message as DBMessage
from models.general import ConversationCreate, MessageCreate
from fastapi.responses import StreamingResponse

chats_router = APIRouter(prefix="/chats")


@chats_router.post("/chat")
async def chat(
    request: Request,
    prompt: str,
    conversation_id: str,
    session: Session = Depends(get_session),
):
    current_user = request.state.user
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
                name=current_user.email.split("@")[0] if current_user.email else None,
            )
            session.add(user)
            session.commit()

        conversation = Conversation(
            id=conversation_id,
            title=await gemini(prompt),  # Generate title using Gemini
            user_id=current_user.uid,
        )
        session.add(conversation)
        session.commit()

    # Get message history from the conversation
    message_history = get_message_history(conversation)

    ##refresh system prompt
    memory = get_memory_no_context(request.state.user.uid, prompt)

    # print("memory", memory[1])

    # save memory to file

    if len(message_history) > 0:
        system_prompt = message_history[0].parts[0].content
        if system_prompt:
            message_history[0].parts[0].content = get_system_prompt(
                request.state.user, memory
            )

    agent = create_agent(current_user, memory)

    async def generate_chunks() -> AsyncGenerator[
        str, None
    ]:  # Changed return type to str since we're yielding JSON strings
        async with agent.iter(
            deps=MyDeps(user_object=current_user),
            user_prompt=prompt,
            message_history=message_history,
        ) as run:
            async for node in run:
                print("Node type:", type(node))
                # print("node", node, "\n")
                if agent.is_user_prompt_node(node):
                    # print("here",node.request, "\n")
                    pass
                elif agent.is_model_request_node(node):
                    # A model request node => We can stream tokens from the model's request
                    # print("model request", node.request, "\n")

                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart):
                                    yield (
                                        "data: " + event_to_json_string(event) + "\n\n"
                                    )
                                elif isinstance(event.part, ReasoningPart):
                                    yield (
                                        "data: " + event_to_json_string(event) + "\n\n"
                                    )
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    yield (
                                        "data: " + event_to_json_string(event) + "\n\n"
                                    )
                                elif isinstance(event.delta, ReasoningPartDelta):
                                    yield (
                                        "data: " + event_to_json_string(event) + "\n\n"
                                    )
                    # Save the complete message
                    # print(node.request)
                    db_message = DBMessage(
                        content=json.dumps(model_message_to_dict(node.request)),
                        is_user_message=False,
                        conversation_id=conversation_id,
                    )
                    # print("db_message", db_message)
                    session.add(db_message)
                    session.commit()
                elif agent.is_call_tools_node(node):
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            # print("tool call", event)
                            yield "data: " + event_to_json_string(event) + "\n\n"

                    # print(node.model_response)
                    db_message = DBMessage(
                        content=json.dumps(model_message_to_dict(node.model_response)),
                        is_user_message=False,
                        conversation_id=conversation_id,
                    )
                    # print("db_message", db_message)

                    session.add(db_message)
                    session.commit()

    return StreamingResponse(
        generate_chunks(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@chats_router.post("/conversations/", response_model=dict)
def create_conversation(
    request: Request,
    conversation: ConversationCreate,
    session: Session = Depends(get_session),
):
    # Users can only create conversations for themselves
    current_user = request.state.user
    if conversation.user_id != current_user.uid:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only create conversations for yourself",
        )

    user = session.get(User, conversation.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_conversation = Conversation(
        title=conversation.title, user_id=conversation.user_id
    )
    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)
    return {"status": "success", "conversation": db_conversation}


@chats_router.get("/conversations/{conversation_id}", response_model=dict)
def read_conversation(
    request: Request,
    conversation_id: str,
    session: Session = Depends(get_session),
):
    current_user = request.state.user
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Users can only access their own conversations
    if conversation.user_id != current_user.uid:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only view your own conversations",
        )

    return {"status": "success", "conversation": conversation}


@chats_router.get("/users/{user_id}/conversations", response_model=dict)
def read_user_conversations(
    request: Request,
    user_id: str,
    session: Session = Depends(get_session),
):
    current_user = request.state.user
    # Users can only access their own conversations
    if user_id != current_user.uid:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only view your own conversations",
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "conversations": user.conversations}


@chats_router.post("/messages/", response_model=dict)
def create_message(
    request: Request,
    message: MessageCreate,
    session: Session = Depends(get_session),
):
    current_user = request.state.user
    conversation = session.get(Conversation, message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Users can only add messages to their own conversations
    if conversation.user_id != current_user.uid:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only add messages to your own conversations",
        )

    db_message = DBMessage(
        content=message.content,
        is_user_message=message.is_user_message,
        conversation_id=message.conversation_id,
    )
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return {"status": "success", "message": db_message}


@chats_router.get("/conversations/{conversation_id}/messages", response_model=dict)
def read_conversation_messages(
    request: Request,
    conversation_id: str,
    session: Session = Depends(get_session),
):
    current_user = request.state.user
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Users can only view messages from their own conversations
    if conversation.user_id != current_user.uid:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only view messages from your own conversations",
        )

    return {"status": "success", "messages": conversation.messages}


def event_to_json_string(event):
    """Convert event objects to JSON string."""
    event_type = "part_start"
    if isinstance(event, PartDeltaEvent):
        event_type = "part_delta"
    elif isinstance(event, FunctionToolCallEvent):
        event_type = "tool_call"
    elif isinstance(event, FunctionToolResultEvent):
        event_type = "tool_result"

    event_dict = {"type": event_type, "data": event_to_dict(event)}
    return json.dumps(event_dict)


def event_from_json_string(json_str):
    """Convert JSON string back to event object."""
    data = json.loads(json_str)
    event_data = data["data"]

    if data["type"] == "part_start":
        return PartStartEvent(
            index=event_data["index"],
            part=TextPart(
                content=event_data["part"]["content"],
                part_kind=event_data["part"]["part_kind"],
            ),
            event_kind=event_data["event_kind"],
        )
    elif data["type"] == "part_delta":
        return PartDeltaEvent(
            index=event_data["index"],
            delta=TextPartDelta(
                content_delta=event_data["delta"]["content"],
                part_delta_kind=event_data["delta"]["part_kind"],
            ),
            event_kind=event_data["event_kind"],
        )
    elif data["type"] == "tool_call":
        return FunctionToolCallEvent(
            part=ToolCallPart(
                tool_name=event_data["tool_call"]["name"],
                args=event_data["tool_call"]["args"],
                tool_call_id=event_data["tool_call"]["tool_call_id"],
            ),
            event_kind=event_data["event_kind"],
        )
    elif data["type"] == "tool_result":
        tool_result = event_data["tool_result"]
        if "content" in tool_result:
            return FunctionToolResultEvent(
                result=ToolReturnPart(
                    tool_name=tool_result["name"],
                    content=tool_result["content"],
                    tool_call_id=tool_result["tool_call_id"],
                ),
                tool_call_id=event_data["tool_call_id"],
                event_kind=event_data["event_kind"],
            )
        elif "retry_prompt" in tool_result:
            # Handle retry prompt case
            return FunctionToolResultEvent(
                result=RetryPromptPart(
                    content=tool_result["retry_prompt"],
                    tool_call_id=tool_result["tool_call_id"],
                ),
                tool_call_id=event_data["tool_call_id"],
                event_kind=event_data["event_kind"],
            )
        else:
            print(f"Unknown tool result format: {tool_result}")
            return None
    return None


def event_to_dict(event):
    """Convert event objects to serializable dictionaries."""
    if isinstance(event, PartStartEvent):
        if isinstance(event.part, TextPart):
            return {
                "index": event.index,
                "part": {
                    "content": event.part.content,
                    "part_kind": event.part.part_kind,
                }
                if event.part
                else None,
                "event_kind": event.event_kind,
            }
        elif isinstance(event.part, ReasoningPart):
            return {
                "index": event.index,
                "part": {
                    "reasoning": event.part.reasoning,
                    "part_kind": event.part.part_kind,
                },
                "event_kind": event.event_kind,
            }
    elif isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            return {
                "index": event.index,
                "delta": {
                    "content": event.delta.content_delta,
                    "part_kind": event.delta.part_delta_kind,
                }
                if event.delta
                else None,
                "event_kind": event.event_kind,
            }
        elif isinstance(event.delta, ReasoningPartDelta):
            return {
                "index": event.index,
                "delta": {
                    "reasoning": event.delta.reasoning_delta,
                    "part_kind": event.delta.part_delta_kind,
                },
                "event_kind": event.event_kind,
            }
    elif isinstance(event, FunctionToolCallEvent):
        return {
            "tool_call": {
                "name": event.part.tool_name,
                "args": event.part.args,
                "tool_call_id": event.part.tool_call_id,
            },
            "call_id": event.call_id,
            "event_kind": event.event_kind,
        }
    elif isinstance(event, FunctionToolResultEvent):
        return {
            "tool_result": {
                "name": event.result.tool_name,
                "content": event.result.content,
                "tool_call_id": event.result.tool_call_id,
                "timestamp": event.result.timestamp.isoformat(),
            },
            "tool_call_id": event.tool_call_id,
            "event_kind": event.event_kind,
        }
    return vars(event)


def model_message_to_dict(message: Union[ModelRequest, ModelResponse]) -> dict:
    """Convert a ModelRequest or ModelResponse to a dictionary for storage"""

    def part_to_dict(part):
        if isinstance(part, ToolCallPart):
            content = {
                "name": part.tool_name,
                "args": part.args,
                "tool_call_id": part.tool_call_id,
            }
        elif isinstance(part, ReasoningPart):
            content = part.reasoning
        elif isinstance(part, UserPromptPart):
            content = part.content
        elif isinstance(part, TextPart):
            content = part.content
        elif isinstance(part, SystemPromptPart):
            content = part.content
        elif isinstance(part, RetryPromptPart):
            content = part.content
        elif isinstance(part, ToolReturnPart):
            # print("I am here", part)
            content = {
                "name": part.tool_name,
                "content": part.content,
                "tool_call_id": part.tool_call_id,
            }
        return {
            "type": part.__class__.__name__,
            "content": content,
            "part_kind": part.part_kind if hasattr(part, "part_kind") else "text",
        }

    if isinstance(message, ModelRequest):
        return {
            "type": "model_request",
            "parts": [part_to_dict(part) for part in message.parts],
            "kind": message.kind,
        }
    else:  # ModelResponse
        return {
            "type": "model_response",
            "parts": [part_to_dict(part) for part in message.parts],
            "model_name": message.model_name,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "kind": message.kind,
        }


def dict_to_model_message(data: dict) -> Union[ModelRequest, ModelResponse]:
    """Convert a dictionary back to a ModelRequest or ModelResponse"""
    parts = []
    for part_data in data["parts"]:
        if part_data["type"] == "ToolCallPart":
            # print(part_data)
            parts.append(
                ToolCallPart(
                    tool_name=part_data["content"].get("name"),
                    args=part_data["content"].get("args"),
                    tool_call_id=part_data["content"].get("tool_call_id"),
                    part_kind=part_data.get("part_kind", "text"),
                )
            )
        elif part_data["type"] == "ReasoningPart":
            parts.append(
                ReasoningPart(
                    reasoning=part_data["content"],
                    part_kind=part_data.get("part_kind", "reasoning"),
                )
            )
        elif part_data["type"] == "UserPromptPart":
            parts.append(
                UserPromptPart(
                    content=part_data["content"],
                    part_kind=part_data.get("part_kind", "text"),
                )
            )
        elif part_data["type"] == "TextPart":
            parts.append(
                TextPart(
                    content=part_data["content"],
                    part_kind=part_data.get("part_kind", "text"),
                )
            )
        elif part_data["type"] == "SystemPromptPart":
            parts.append(
                SystemPromptPart(
                    content=part_data["content"],
                    part_kind=part_data.get("part_kind", "text"),
                )
            )
        elif part_data["type"] == "RetryPromptPart":
            parts.append(
                RetryPromptPart(
                    content=part_data["content"],
                    part_kind=part_data.get("part_kind", "text"),
                )
            )
        elif part_data["type"] == "ToolReturnPart":
            parts.append(
                ToolReturnPart(
                    tool_name=part_data["content"].get("name"),
                    content=part_data["content"].get("content"),
                    tool_call_id=part_data["content"].get("tool_call_id"),
                    part_kind=part_data.get("part_kind", "text"),
                )
            )
    if data["type"] == "model_request":
        return ModelRequest(parts=parts, kind="request")
    else:  # model_response
        return ModelResponse(
            parts=parts,
            model_name=data.get("model_name"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if data.get("timestamp")
            else datetime.now(),
            kind="response",
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
