"""Tests for list_tables node"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.chat_workflow.nodes.list_tables import list_tables_node
from src.models.chat_models import ChatState


class TestListTablesNode:
    """Test list_tables_node function"""

    @patch("src.chat_workflow.nodes.list_tables.get_sql_database")
    def test_list_tables_success(self, mock_get_db):
        """Test successful table listing"""
        # Mock database
        mock_db = MagicMock()
        mock_db.get_usable_table_names.return_value = [
            "emails_processed",
            "product_mentions",
            "inventory_items",
        ]
        mock_get_db.return_value = mock_db

        # Create initial state
        state = ChatState()

        # Execute node
        result = list_tables_node(state)

        # Verify results
        assert "available_tables" in result
        assert len(result["available_tables"]) == 3
        assert "emails_processed" in result["available_tables"]
        assert "product_mentions" in result["available_tables"]
        assert "inventory_items" in result["available_tables"]

        # Verify message
        assert "messages" in result
        assert len(result["messages"]) == 1
        message = result["messages"][0]
        assert isinstance(message, AIMessage)
        assert "emails_processed" in message.content
        assert "product_mentions" in message.content

    @patch("src.chat_workflow.nodes.list_tables.get_sql_database")
    def test_list_tables_handles_all_westbrand_tables(self, mock_get_db):
        """Test that all WestBrand tables are included"""
        # Mock database with all tables
        mock_db = MagicMock()
        mock_db.get_usable_table_names.return_value = [
            "emails_processed",
            "product_mentions",
            "inventory_items",
            "inventory_matches",
            "match_review_flags",
        ]
        mock_get_db.return_value = mock_db

        state = ChatState()
        result = list_tables_node(state)

        # Verify all tables present
        assert len(result["available_tables"]) == 5
        expected_tables = {
            "emails_processed",
            "product_mentions",
            "inventory_items",
            "inventory_matches",
            "match_review_flags",
        }
        assert set(result["available_tables"]) == expected_tables

    @patch("src.chat_workflow.nodes.list_tables.get_sql_database")
    def test_list_tables_error_handling(self, mock_get_db):
        """Test error handling when database access fails"""
        # Mock database to raise exception
        mock_get_db.side_effect = Exception("Database connection failed")

        state = ChatState()
        result = list_tables_node(state)

        # Verify error is captured
        assert "error" in result
        assert "Database connection failed" in result["error"]

        # Verify error message is created
        assert "messages" in result
        assert len(result["messages"]) == 1
        message = result["messages"][0]
        assert isinstance(message, AIMessage)
        assert "Error listing tables" in message.content

    @patch("src.chat_workflow.nodes.list_tables.get_sql_database")
    def test_list_tables_returns_dict_for_langgraph(self, mock_get_db):
        """Test that node returns dict (required for LangGraph state updates)"""
        mock_db = MagicMock()
        mock_db.get_usable_table_names.return_value = ["test_table"]
        mock_get_db.return_value = mock_db

        state = ChatState()
        result = list_tables_node(state)

        # Verify return type is dict (LangGraph requirement)
        assert isinstance(result, dict)
        assert "available_tables" in result
        assert "messages" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
