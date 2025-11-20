"""List tables node for SQL chat agent"""

from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.chat_workflow.models import ChatState
from src.chat_workflow.utils.db_wrapper import get_sql_database


def list_tables_node(state: ChatState) -> Dict[str, Any]:
    """
    List all available database tables.

    This node is executed at the start of the workflow to provide
    the agent with context about available tables.

    Args:
        state: Current chat state

    Returns:
        Dict with updated state containing:
        - available_tables: List of table names
        - messages: AIMessage with table list
    """
    try:
        db = get_sql_database()
        tables = db.get_usable_table_names()

        # Create informative message about available tables
        table_list = ", ".join(tables)
        message = AIMessage(content=f"Available database tables: {table_list}")

        return {"available_tables": tables, "messages": [message]}

    except Exception as e:
        # Handle errors gracefully
        error_message = AIMessage(content=f"Error listing tables: {str(e)}")
        return {"error": str(e), "messages": [error_message]}
