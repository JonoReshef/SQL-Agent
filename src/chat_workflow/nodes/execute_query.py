"""Execute query node for SQL chat agent"""

from typing import Any, Dict

from langchain_core.messages import AIMessage, ToolMessage

from src.chat_workflow.utils.tools import run_query_tool
from src.models.chat_models import ChatState, QueryExecution


def execute_query_node(state: ChatState) -> Dict[str, Any]:
    """
    Execute SQL query from tool call.

    This node:
    1. Extracts SQL query from tool call
    2. Validates it's a SELECT query
    3. Executes against database
    4. Generates human-readable explanation and summary
    5. Returns formatted results with transparency details

    Args:
        state: Current chat state with query tool call

    Returns:
        Dict with messages containing query results and QueryExecution objects with explanations
    """

    tool_messages = []
    executed_queries = state.executed_queries.copy()

    # Execute each tool call
    for tool_call in state.query_result.tool_calls:  # type: ignore
        if tool_call["name"] == "run_query_tool":
            # Extract query from tool call
            query = tool_call["args"].get("query", "")

            # Execute the tool
            result = run_query_tool.invoke({"query": query})

            # Create QueryExecution object with full details
            query_execution = QueryExecution(
                query=query,
                raw_result=result,
            )
            executed_queries.append(query_execution)

            # Create tool message with result
            tool_message = ToolMessage(content=result, tool_call_id=tool_call["id"])
            tool_messages.append(tool_message)

    return {
        "executed_queries": executed_queries,
        "current_query": executed_queries[-1].query if executed_queries else None,
        "execute_result": tool_messages[-1].content if tool_messages else None,
    }
