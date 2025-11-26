"""Tests for LangGraph workflow"""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.chat_workflow.graph import create_chat_graph, should_continue
from src.models.chat_models import ChatState


class TestShouldContinue:
    """Test should_continue routing function"""

    def test_should_continue_with_tool_calls(self):
        """Test routing when message has tool calls"""
        ai_message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "run_query_tool",
                    "args": {"query": "SELECT * FROM test"},
                    "id": "call_123",
                }
            ],
        )
        state = ChatState(messages=[ai_message])

        result = should_continue(state)

        assert result == "execute_query"

    def test_should_continue_without_tool_calls(self):
        """Test routing when message has no tool calls"""
        ai_message = AIMessage(content="Here's your answer")
        state = ChatState(messages=[ai_message])

        result = should_continue(state)

        assert result == "generate_explanations"

    def test_should_continue_empty_state(self):
        """Test routing with empty message list"""
        state = ChatState(messages=[])

        result = should_continue(state)

        assert result == "generate_explanations"

    def test_should_continue_human_message(self):
        """Test routing with human message (no tool_calls attribute)"""
        human_message = HumanMessage(content="What's in the database?")
        state = ChatState(messages=[human_message])

        result = should_continue(state)

        assert result == "generate_explanations"


class TestCreateChatGraph:
    """Test create_chat_graph function"""

    @patch.dict(os.environ, {}, clear=True)
    def test_create_chat_graph_missing_database_url(self):
        """Test that missing DATABASE_URL raises error"""
        with pytest.raises(ValueError, match="DATABASE_URL environment variable not set"):
            create_chat_graph()

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost:5432/testdb"})
    @patch("src.chat_workflow.graph.PostgresSaver")
    def test_create_chat_graph_success(self, mock_saver_class):
        """Test successful graph creation"""
        # Mock PostgresSaver context manager
        mock_saver = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_saver
        mock_saver_class.from_conn_string.return_value = mock_context_manager

        # Create graph
        graph = create_chat_graph()

        # Verify checkpointer was created
        mock_saver_class.from_conn_string.assert_called_once_with(
            "postgresql://test:test@localhost:5432/testdb"
        )
        mock_context_manager.__enter__.assert_called_once()
        mock_saver.setup.assert_called_once()

        # Verify graph was created
        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost:5432/testdb"})
    @patch("src.chat_workflow.graph.PostgresSaver")
    def test_create_chat_graph_has_all_nodes(self, mock_saver_class):
        """Test that graph contains all expected nodes"""
        # Mock PostgresSaver context manager
        mock_saver = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_saver
        mock_saver_class.from_conn_string.return_value = mock_context_manager

        # Create graph
        graph = create_chat_graph()

        # Get graph structure
        graph_dict = graph.get_graph().to_json()

        # Verify all nodes are present
        assert "list_tables" in str(graph_dict)
        assert "get_schema" in str(graph_dict)
        assert "generate_query" in str(graph_dict)
        assert "execute_query" in str(graph_dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
