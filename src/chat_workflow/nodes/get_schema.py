"""Get schema node for SQL chat agent"""

from langchain_core.tools import tool

from src.chat_workflow.utils.db_wrapper import get_sql_database


@tool
def get_schema_tool(table_names: str) -> str:
    """
    Get database schema for specified tables.

    Args:
        table_names: Comma-separated list of table names

    Returns:
        Schema information including CREATE statements and sample rows
    """
    try:
        db = get_sql_database()
        # Parse comma-separated table names
        tables = [t.strip() for t in table_names.split(",")]

        # Get schema info
        schema_info = db.get_table_info_no_throw(tables)

        if not schema_info:
            return f"No schema information found for tables: {table_names}"

        return schema_info

    except Exception as e:
        return f"Error getting schema: {str(e)}"
