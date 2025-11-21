"""Pydantic models for SQL chat agent state"""

from operator import add
from typing import Annotated, List, Optional

from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel, ConfigDict, Field


class QuestionEnrichment(BaseModel):
    """
    Enrichment details for a user question.

    This model captures additional context or clarifying questions
    generated to better understand the user's intent.
    """

    additional_questions: List[str] = Field(
        ...,
        description="List of additional clarifying questions generated to better understand the user's intent",
    )
    intended_goal: Optional[str] = Field(
        default=None,
        description="Explanation of how these additional questions help achieve the user's intended goal",
    )


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
    query_explanation: QueryExplanation | None = Field(
        default=None,
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

    user_question: str = Field(
        default="",
        description="The current user question to be answered",
    )
    anticipate_complexity: bool = Field(
        default=False,
        description="Whether to use thorough/exploratory analysis (True) or direct answers (False)",
    )
    enriched_query: QuestionEnrichment = Field(
        default=QuestionEnrichment(additional_questions=[]),
        description="The enriched user question with additional context",
    )
    query_result: AIMessage = Field(
        default=AIMessage(content=""),
        description="The AIMessage containing the result of the last query",
    )
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
    execute_result: Optional[str] = Field(
        default=None, description="Result from the last executed query"
    )
    error: Optional[str] = Field(default=None, description="Error message from failed operations")
    executed_queries: List[QueryExecution] = Field(
        default_factory=list,
        description="Detailed list of all SQL queries executed with explanations and summaries (for transparency)",
    )
    executed_queries_enriched: List[QueryExecution] = Field(
        default_factory=list,
        description="Detailed list of all SQL queries executed with explanations and summaries (for transparency)",
    )
    overall_summary: Optional[str] = Field(
        default=None, description="Explain the entire search process in a concise summary"
    )
