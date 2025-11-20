"""Pydantic models for SQL chat agent state"""

from operator import add
from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, Field


class QueryExplanation(BaseModel):
    """
    Explanation of a SQL query execution.

    This model captures everything needed to explain what happened
    during query execution in human-readable terms.
    """

    description: str = Field(
        ...,
        description="One-line non-technical explanation of what this query does.",
    )
    result_summary: str | None = Field(
        ...,
        description="Brief summary of what the query returned (e.g., 'Found 80 records which were used to narrow down the search area from [large category] to [smaller category]' or 'No matching data')",
    )


class QueryExecution(BaseModel):
    """
    Details about a single SQL query execution for transparency.

    This model captures everything needed to explain what happened
    during query execution in human-readable terms.
    """

    query: str = Field(..., description="The actual SQL query that was executed")
    query_explanation: QueryExplanation = Field(
        ...,
        description="One-line human-readable explanation of what this query does (non-technical)",
    )
    raw_result: Optional[str] = Field(
        default=None, description="The raw query result from the database"
    )


class ChatState(BaseModel):
    """
    LangGraph state for SQL chat agent (Pydantic v2).

    State management follows LangGraph MessagesState pattern with:
    - Message history using add reducer (never overwrites)
    - Available database tables list
    - Current query tracking
    - Query result storage
    - Error handling
    - SQL query transparency tracking
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
    executed_queries: Annotated[List[QueryExecution], add] = Field(
        default_factory=list,
        description="Detailed list of all SQL queries executed with explanations and summaries (for transparency)",
    )
