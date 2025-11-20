"""LangGraph workflow for SQL chat agent"""

import os
from typing import Literal

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from src.chat_workflow.nodes.execute_query import execute_query_node
from src.chat_workflow.nodes.generate_query import generate_query_node
from src.chat_workflow.nodes.get_schema import get_schema_tool
from src.chat_workflow.nodes.list_tables import list_tables_node
from src.models.chat_models import ChatState

load_dotenv()

# Module-level storage for checkpointer context manager
# This ensures the connection stays alive for the lifetime of the module
_checkpointer_cm = None
_checkpointer = None


def should_continue(state: ChatState) -> Literal["execute_query", "__end__"]:
    """
    Determine whether to execute query or end workflow.

    Args:
        state: Current chat state

    Returns:
        Next node name or END
    """
    # Get the last message
    if not state.messages:
        return "__end__"

    last_message = state.messages[-1]

    # Check if last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore
        return "execute_query"

    # No tool calls means LLM provided final answer
    return "__end__"


def _get_checkpointer():
    """
    Get or create PostgreSQL checkpointer singleton.

    This manages the checkpointer context manager lifecycle properly
    by storing it at module level, ensuring the connection stays alive.

    Returns:
        PostgresSaver instance with active connection
    """
    global _checkpointer_cm, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    # Get DATABASE_URL for checkpointer
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Create and enter the context manager
    # Store both the context manager and the checkpointer to keep connection alive
    _checkpointer_cm = PostgresSaver.from_conn_string(database_url)
    _checkpointer = _checkpointer_cm.__enter__()
    _checkpointer.setup()  # Creates checkpoint tables if they don't exist

    return _checkpointer


def create_chat_graph() -> CompiledStateGraph:
    """
    Create the SQL chat agent workflow graph.

    Workflow:
    1. List Tables: Discover available database tables
    2. Get Schema: Fetch table schemas (ToolNode)
    3. Generate Query: Convert natural language to SQL
    4. Execute Query: Run SQL and return results (conditional)
    5. Loop back to Generate Query for follow-ups

    Returns:
        Compiled StateGraph with PostgreSQL checkpointer for persistence

    Note:
        The checkpointer connection is managed at module level to ensure
        it stays alive for the lifetime of the application.
    """
    # Get or create checkpointer (singleton pattern)
    checkpointer = _get_checkpointer()

    # Create state graph
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("list_tables", list_tables_node)
    workflow.add_node("get_schema", ToolNode([get_schema_tool]))
    workflow.add_node("generate_query", generate_query_node)
    workflow.add_node("execute_query", execute_query_node)  # Use custom node for query tracking

    # Define workflow edges
    # Start -> List Tables (discover schema)
    workflow.add_edge("__start__", "list_tables")

    # List Tables -> Get Schema (get detailed table info)
    workflow.add_edge("list_tables", "get_schema")

    # Get Schema -> Generate Query (create SQL from user question)
    workflow.add_edge("get_schema", "generate_query")

    # Generate Query -> Conditional (execute query if tool call, else end)
    workflow.add_conditional_edges(
        "generate_query", should_continue, {"execute_query": "execute_query", "__end__": END}
    )

    # Execute Query -> Generate Query (loop for follow-up questions)
    workflow.add_edge("execute_query", "generate_query")

    # Compile with checkpointer
    return workflow.compile(checkpointer=checkpointer)
