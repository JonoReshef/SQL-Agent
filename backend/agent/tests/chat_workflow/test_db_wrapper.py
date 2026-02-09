"""Tests for database wrapper utilities"""

import os
from unittest.mock import MagicMock, patch

import pytest

from agent.chat_workflow.utils.db_wrapper import (
    get_sql_database,
    get_sql_tools,
    validate_query_is_select,
)


class TestValidateQueryIsSelect:
    """Test SQL query validation for read-only enforcement"""

    def test_valid_select_query(self):
        """Test that valid SELECT queries pass validation"""
        query = "SELECT * FROM emails_processed LIMIT 10"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is True
        assert error == ""

    def test_select_with_joins(self):
        """Test SELECT with JOINs is allowed"""
        query = """
        SELECT pm.product_name, e.subject 
        FROM product_mentions pm 
        JOIN emails_processed e ON pm.email_thread_hash = e.thread_hash
        """
        is_valid, error = validate_query_is_select(query)

        assert is_valid is True
        assert error == ""

    def test_select_with_leading_whitespace(self):
        """Test SELECT with leading whitespace is allowed"""
        query = "   \n  SELECT COUNT(*) FROM product_mentions"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is True
        assert error == ""

    def test_insert_query_rejected(self):
        """Test that INSERT queries are rejected"""
        query = "INSERT INTO emails_processed (thread_hash) VALUES ('abc123')"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "INSERT" in error
        assert "forbidden" in error.lower()

    def test_update_query_rejected(self):
        """Test that UPDATE queries are rejected"""
        query = "UPDATE product_mentions SET product_name = 'Test' WHERE id = 1"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "UPDATE" in error

    def test_delete_query_rejected(self):
        """Test that DELETE queries are rejected"""
        query = "DELETE FROM emails_processed WHERE thread_hash = 'abc'"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "DELETE" in error

    def test_drop_query_rejected(self):
        """Test that DROP queries are rejected"""
        query = "DROP TABLE emails_processed"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "DROP" in error

    def test_alter_query_rejected(self):
        """Test that ALTER queries are rejected"""
        query = "ALTER TABLE emails_processed ADD COLUMN test VARCHAR(255)"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "ALTER" in error

    def test_create_query_rejected(self):
        """Test that CREATE queries are rejected"""
        query = "CREATE TABLE test (id INT)"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "CREATE" in error

    def test_truncate_query_rejected(self):
        """Test that TRUNCATE queries are rejected"""
        query = "TRUNCATE TABLE emails_processed"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "TRUNCATE" in error

    def test_non_select_start_rejected(self):
        """Test that queries not starting with SELECT are rejected"""
        query = "EXPLAIN SELECT * FROM emails_processed"
        is_valid, error = validate_query_is_select(query)

        assert is_valid is False
        assert "must start with SELECT" in error


class TestGetSQLDatabase:
    """Test SQLDatabase wrapper creation"""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_database_url_raises_error(self):
        """Test that missing DATABASE_URL raises ValueError"""
        # Clear the lru_cache to force re-evaluation
        get_sql_database.cache_clear()

        with pytest.raises(
            ValueError, match="DATABASE_URL environment variable not set"
        ):
            get_sql_database()

    @patch.dict(
        os.environ, {"DATABASE_URL": "postgresql://test:test@localhost:5432/testdb"}
    )
    @patch("src.chat_workflow.utils.db_wrapper.SQLDatabase")
    def test_creates_database_with_correct_tables(self, mock_sql_database):
        """Test that SQLDatabase is created with WestBrand tables"""
        # Clear the lru_cache
        get_sql_database.cache_clear()

        # Mock the from_uri method
        mock_db_instance = MagicMock()
        mock_sql_database.from_uri.return_value = mock_db_instance

        _ = get_sql_database()  # Call the function to test

        # Verify from_uri was called with correct parameters
        mock_sql_database.from_uri.assert_called_once()
        call_args = mock_sql_database.from_uri.call_args

        assert call_args[0][0] == "postgresql://test:test@localhost:5432/testdb"
        assert "include_tables" in call_args[1]

        included_tables = call_args[1]["include_tables"]
        assert "emails_processed" in included_tables
        assert "product_mentions" in included_tables
        assert "inventory_items" in included_tables
        assert "inventory_matches" in included_tables
        assert "match_review_flags" in included_tables


class TestGetSQLTools:
    """Test SQL tools creation"""

    @patch("src.chat_workflow.utils.db_wrapper.get_sql_database")
    @patch("src.chat_workflow.utils.db_wrapper.SQLDatabaseToolkit")
    def test_returns_only_read_only_tools(self, mock_toolkit_class, mock_get_db):
        """Test that only read-only tools are returned"""
        # Create mock tools
        mock_query_tool = MagicMock(name="sql_db_query")
        mock_schema_tool = MagicMock(name="sql_db_schema")
        mock_list_tool = MagicMock(name="sql_db_list_tables")
        mock_checker_tool = MagicMock(name="sql_db_query_checker")

        # Set tool names
        mock_query_tool.name = "sql_db_query"
        mock_schema_tool.name = "sql_db_schema"
        mock_list_tool.name = "sql_db_list_tables"
        mock_checker_tool.name = "sql_db_query_checker"

        # Mock toolkit instance
        mock_toolkit = MagicMock()
        mock_toolkit.get_tools.return_value = [
            mock_query_tool,
            mock_schema_tool,
            mock_list_tool,
            mock_checker_tool,
        ]
        mock_toolkit_class.return_value = mock_toolkit

        # Mock LLM
        mock_llm = MagicMock()

        # Get tools
        tools = get_sql_tools(mock_llm)

        # Verify only read-only tools are returned
        assert len(tools) == 3
        tool_names = {tool.name for tool in tools}
        assert "sql_db_query" in tool_names
        assert "sql_db_schema" in tool_names
        assert "sql_db_list_tables" in tool_names
        assert "sql_db_query_checker" not in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
