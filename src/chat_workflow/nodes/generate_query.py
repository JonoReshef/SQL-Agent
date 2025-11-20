"""Generate query node for SQL chat agent"""

from typing import Any, Dict

from langchain_core.messages import AIMessage, SystemMessage

from src.chat_workflow.models import ChatState
from src.chat_workflow.prompts import WESTBRAND_SYSTEM_PROMPT
from src.chat_workflow.utils.tools import run_query_tool
from src.llm.client import get_llm_client


def generate_query_node(state: ChatState) -> Dict[str, Any]:
    """
    Generate SQL query from user question using LLM.

    This node uses the LLM with tool binding to convert natural language
    questions into SQL queries.

    Args:
        state: Current chat state with user message

    Returns:
        Dict with AIMessage containing tool call or final response
    """
    try:
        # Get LLM client with default settings (gpt5-low)
        llm = get_llm_client()

        # Bind the run_query tool to LLM
        llm_with_tools = llm.bind_tools([run_query_tool])  # type: ignore

        # Build messages for LLM
        # Include system prompt first
        system_message = SystemMessage(WESTBRAND_SYSTEM_PROMPT)

        # Convert state messages to format LLM expects
        messages = [system_message] + state.messages

        # Generate the SQL query
        response = llm_with_tools.invoke(messages)

        return {"messages": [response]}

    except Exception as e:
        error_message = AIMessage(content=f"Error generating query: {str(e)}")
        return {"error": str(e), "messages": [error_message]}
