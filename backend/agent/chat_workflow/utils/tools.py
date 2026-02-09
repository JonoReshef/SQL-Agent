from functools import lru_cache

import tiktoken
from langchain_core.tools import tool

from agent.chat_workflow.utils.db_wrapper import (
    get_sql_database,
    validate_query_is_select,
)

ENCODER = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS = 50000


@tool
def run_query_tool(query: str) -> str:
    """
    Execute a SQL query against the database (SELECT only).

    Args:
        query: SQL query to execute

    Returns:
        Query results as formatted string
    """
    print("Running 'run_query_tool' with query:", query)
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

        total_tokens = ENCODER.encode(str(result))
        if len(total_tokens) > MAX_TOKENS:
            return f"Query executed successfully however the result returned {len(total_tokens)} tokens which is larger than the maximum allowed {MAX_TOKENS} tokens."

        return result  # type: ignore

    except Exception as e:
        return f"Error executing query: {str(e)}"


@tool
@lru_cache(maxsize=1)
def get_schema_tool(table_names: str) -> str:
    """
    Get database schema for specified tables.

    Args:
        table_names: Comma-separated list of table names

    Returns:
        Schema information including CREATE statements and sample rows
    """
    print("Running 'get_schema_tool' for tables:", table_names)
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
