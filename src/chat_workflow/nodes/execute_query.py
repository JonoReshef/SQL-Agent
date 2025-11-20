"""Execute query node for SQL chat agent"""

from typing import Any, Dict

from langchain_core.messages import ToolMessage

from src.chat_workflow.prompts import EXPLANATION_PROMPT
from src.chat_workflow.utils.tools import run_query_tool
from src.llm.client import get_llm_client
from src.models.chat_models import ChatState, QueryExecution, QueryExplanation

LLM = get_llm_client()
LLM_STRUCTURED = get_llm_client(output_structure=QueryExplanation)


def _generate_query_explanation_and_summary(query: str, result: str) -> QueryExplanation:
    """
    Generate human-readable explanation and result summary for a SQL query.

    Args:
        query: The SQL query that was executed
        result: The result returned from the query

    Returns:
        Tuple of (explanation, result_summary)
    """
    try:
        response = QueryExplanation.model_validate(
            LLM_STRUCTURED.invoke(EXPLANATION_PROMPT.format(query=query, result=result))
        )

        return response

    except Exception as e:
        # Fallback to generic messages if LLM fails
        print(f"   Warning: Failed to generate query explanation - {str(e)}")
        return QueryExplanation(
            description="Unable to generate explanation",
            result_summary=None,
        )


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
    # Get the last message which should contain tool calls
    last_message = state.messages[-1] if state.messages else None

    if not last_message or not hasattr(last_message, "tool_calls") or not last_message.tool_calls:  # type: ignore
        # No tool calls to execute
        return {"messages": []}

    tool_messages = []
    executed_queries = []

    # Execute each tool call
    for tool_call in last_message.tool_calls:  # type: ignore
        if tool_call["name"] == "run_query_tool":
            # Extract query from tool call
            query = tool_call["args"].get("query", "")

            # Execute the tool
            result = run_query_tool.invoke({"query": query})

            # Generate explanation and summary
            explanation = _generate_query_explanation_and_summary(query, result)

            # Create QueryExecution object with full details
            query_execution = QueryExecution(
                query=query,
                query_explanation=explanation,
                raw_result=result,
            )
            executed_queries.append(query_execution)

            # Create tool message with result
            tool_message = ToolMessage(content=result, tool_call_id=tool_call["id"])
            tool_messages.append(tool_message)

    return {
        "messages": tool_messages,
        "executed_queries": executed_queries,
        "current_query": executed_queries[-1].query if executed_queries else None,
        "query_result": tool_messages[-1].content if tool_messages else None,
    }
