"""Pydantic models for SQL chat agent state"""

from operator import add
from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, Field


class ChatState(BaseModel):
    """
    LangGraph state for SQL chat agent (Pydantic v2).

    State management follows LangGraph MessagesState pattern with:
    - Message history using add reducer (never overwrites)
    - Available database tables list
    - Current query tracking
    - Query result storage
    - Error handling
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)  # Pydantic v2 config

    messages: Annotated[List[BaseMessage], add] = Field(
        default_factory=list,
        description="Conversation history with add reducer for appending messages",
    )
    available_tables: List[str] = Field(
        default_factory=list, description="List of database tables accessible to the agent"
    )
    current_query: Optional[str] = Field(
        default=None, description="SQL query currently being executed"
    )
    query_result: Optional[str] = Field(
        default=None, description="Result from the last executed query"
    )
    error: Optional[str] = Field(default=None, description="Error message from failed operations")
