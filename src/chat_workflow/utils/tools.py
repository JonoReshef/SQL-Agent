from langchain_core.tools import tool

from src.chat_workflow.utils.db_wrapper import get_sql_database, validate_query_is_select


@tool
def run_query_tool(query: str) -> str:
    """
    Execute a SQL query against the database (SELECT only).

    Args:
        query: SQL query to execute

    Returns:
        Query results as formatted string
    """
    try:
        # Validate query is read-only
        is_valid, error_msg = validate_query_is_select(query)
        if not is_valid:
            return f"Query rejected: {error_msg}"

        # Execute query
        db = get_sql_database()
        result = db.run(query)

        if not result or result.strip() == "":  # type: ignore
            return "Query executed successfully but returned no results."

        return result  # type: ignore

    except Exception as e:
        return f"Error executing query: {str(e)}"
