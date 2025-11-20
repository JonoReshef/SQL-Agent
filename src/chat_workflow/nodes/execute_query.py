"""Execute query node for SQL chat agent"""

from typing import Any, Dict

from langchain_core.messages import ToolMessage

from src.chat_workflow.models import ChatState
from src.chat_workflow.utils.tools import run_query_tool


def execute_query_node(state: ChatState) -> Dict[str, Any]:
    """
    Execute SQL query from tool call.

    This node:
    1. Extracts SQL query from tool call
    2. Validates it's a SELECT query
    3. Executes against database
    4. Returns formatted results

    Args:
        state: Current chat state with query tool call

    Returns:
        Dict with messages containing query results
    """
    # Get the last message which should contain tool calls
    last_message = state.messages[-1] if state.messages else None

    if not last_message or not hasattr(last_message, "tool_calls") or not last_message.tool_calls:  # type: ignore
        # No tool calls to execute
        return {"messages": []}

    messages = []

    # Execute each tool call
    for tool_call in last_message.tool_calls:  # type: ignore
        if tool_call["name"] == "run_query_tool":
            # Extract query from tool call
            query = tool_call["args"].get("query", "")

            # Store current query in state
            messages.append({"current_query": query})

            # Execute the tool
            result = run_query_tool.invoke({"query": query})

            # Create tool message with result
            tool_message = ToolMessage(content=result, tool_call_id=tool_call["id"])
            messages.append(tool_message)

            # Store result in state
            messages.append({"query_result": result})

    # If we executed queries, return ToolMessages
    # Filter out dict updates (state updates don't go in messages list)
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

    # Get state updates
    state_updates = {}
    for m in messages:
        if isinstance(m, dict):
            state_updates.update(m)

    return {"messages": tool_messages, **state_updates}
