"""Pydantic models for FastAPI server endpoints"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryExecutionResponse(BaseModel):
    """Response model for query execution details"""

    query: str = Field(..., description="The SQL query that was executed")
    explanation: str = Field(
        ..., description="Human-readable explanation of what the query does"
    )
    result_summary: str = Field(..., description="Brief summary of the query results")


class ChatRequest(BaseModel):
    """Request model for chat endpoints"""

    message: str = Field(..., description="User's question or message")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")
    anticipate_complexity: bool = Field(
        default=False,
        description="Whether to use more thorough/exploratory analysis (True) or direct answers (False)",
    )


class ChatResponse(BaseModel):
    """Response model for non-streaming chat endpoint"""

    response: str = Field(..., description="Agent's response")
    thread_id: str = Field(..., description="Thread ID for this conversation")
    executed_queries: list[QueryExecutionResponse] = Field(
        default_factory=list,
        description="SQL queries executed with explanations and summaries",
    )


class MessageHistory(BaseModel):
    """Single message in conversation history"""

    type: str = Field(..., description="Message type (HumanMessage, AIMessage, etc.)")
    content: str = Field(..., description="Message content")


class CheckpointData(BaseModel):
    """Single checkpoint in conversation history"""

    checkpoint_id: str = Field(..., description="Unique checkpoint identifier")
    messages: list[MessageHistory] = Field(
        default_factory=list, description="Messages in this checkpoint"
    )
    timestamp: Optional[str] = Field(
        None, description="ISO timestamp when checkpoint was created"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional checkpoint metadata"
    )


class HistoryResponse(BaseModel):
    """Response model for history endpoint"""

    thread_id: str = Field(..., description="Thread ID")
    history: list[CheckpointData] = Field(
        default_factory=list, description="List of checkpoint states with messages"
    )


class ChatMessageModel(BaseModel):
    """A single chat message"""

    id: str
    role: str
    content: str
    timestamp: str  # ISO format datetime
    status: Optional[str] = None
    queries: Optional[list[dict[str, Any]]] = None
    overall_summary: Optional[str] = None


class ThreadResponse(BaseModel):
    """Response model for a chat thread"""

    id: str
    title: str
    last_message: str
    timestamp: str  # ISO format datetime
    message_count: int


class ThreadListResponse(BaseModel):
    """Response model for list of threads"""

    threads: list[ThreadResponse]


class CreateThreadRequest(BaseModel):
    """Request model for creating a thread"""

    id: str = Field(..., description="UUID for the new thread")
    title: str = Field(default="New Chat", description="Thread title")


class UpdateThreadRequest(BaseModel):
    """Request model for updating a thread"""

    title: Optional[str] = None
    last_message: Optional[str] = None
    message_count: Optional[int] = None


class SaveMessageRequest(BaseModel):
    """Request model for saving a message"""

    id: str
    role: str
    content: str
    timestamp: str
    status: Optional[str] = None
    queries: Optional[list[dict[str, Any]]] = None
    overall_summary: Optional[str] = None


class UpdateMessageRequest(BaseModel):
    """Request model for updating a message"""

    content: Optional[str] = None
    status: Optional[str] = None
    queries: Optional[list[dict[str, Any]]] = None
    overall_summary: Optional[str] = None


class BulkImportRequest(BaseModel):
    """Request model for importing threads and messages from localStorage"""

    threads: list[CreateThreadRequest]
    messages: dict[str, list[SaveMessageRequest]] = Field(
        default_factory=dict,
        description="Map of thread_id to list of messages",
    )
