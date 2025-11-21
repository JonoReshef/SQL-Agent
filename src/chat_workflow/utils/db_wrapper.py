"""Database wrapper utilities for SQL chat agent"""

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import BaseTool

load_dotenv()

# List of forbidden database keywords (DML/DDL operations)
BLACK_LIST = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "MERGE",
    "GRANT",
    "REVOKE",
]


@lru_cache(maxsize=1)
def get_sql_database() -> SQLDatabase:
    """
    Get SQLDatabase wrapper (cached singleton).

    Returns:
        SQLDatabase instance configured for WestBrand PostgreSQL database

    Raises:
        ValueError: If DATABASE_URL environment variable not set
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Include all WestBrand tables with explicit whitelist
    db = SQLDatabase.from_uri(
        database_url,
        include_tables=[
            "emails_processed",
            "product_mentions",
            "inventory_items",
            "inventory_matches",
            "match_review_flags",
        ],
        sample_rows_in_table_info=3,  # Include sample rows in schema
    )
    return db


def get_sql_tools(llm) -> List[BaseTool]:
    """
    Get SQL database tools for LangGraph (read-only subset).

    Args:
        llm: Language model instance for tool use

    Returns:
        List of read-only SQL tools (query, schema, list_tables)
    """
    db = get_sql_database()
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    # Filter to read-only tools only (no query_checker for simplicity)
    read_only_tool_names = {
        "sql_db_query",  # Execute SELECT queries
        "sql_db_schema",  # Get table schemas
        "sql_db_list_tables",  # List available tables
    }

    tools = [tool for tool in toolkit.get_tools() if tool.name in read_only_tool_names]

    return tools


def validate_query_is_select(query: str) -> tuple[bool, str]:
    """
    Validate that a SQL query is read-only (SELECT statement).

    Args:
        query: SQL query string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if query is valid SELECT
        - (False, error_message) if query contains write operations
    """
    # Normalize query for checking
    query_upper = query.strip().upper()

    # Check for forbidden keywords
    for keyword in BLACK_LIST:
        if keyword in query_upper:
            return (
                False,
                f"Query contains forbidden keyword: {keyword}. Only SELECT queries are allowed.",
            )

    return True, ""
