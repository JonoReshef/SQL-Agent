"""Tests for execute_query node"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from agent.chat_workflow.nodes.execute_query import execute_query_node, run_query_tool
from agent.models.chat_models import ChatState


class TestRunQueryTool:
    """Test run_query_tool function"""

    @patch("src.chat_workflow.utils.tools.get_sql_database")
    def test_run_query_tool_success(self, mock_get_db):
        """Test successful query execution"""
        mock_db = MagicMock()
        mock_db.run.return_value = "[(1, 'test'), (2, 'data')]"
        mock_get_db.return_value = mock_db

        result = run_query_tool.invoke({"query": "SELECT * FROM test_table LIMIT 2"})

        assert "test" in result
        assert "data" in result
        mock_db.run.assert_called_once()

    def test_run_query_tool_rejects_insert(self):
        """Test that INSERT queries are rejected"""
        result = run_query_tool.invoke({"query": "INSERT INTO test VALUES (1)"})

        assert "Query rejected" in result
        assert "INSERT" in result

    def test_run_query_tool_rejects_update(self):
        """Test that UPDATE queries are rejected"""
        result = run_query_tool.invoke({"query": "UPDATE test SET col=1"})

        assert "Query rejected" in result

    def test_run_query_tool_rejects_delete(self):
        """Test that DELETE queries are rejected"""
        result = run_query_tool.invoke({"query": "DELETE FROM test"})

        assert "Query rejected" in result

    @patch("src.chat_workflow.utils.tools.get_sql_database")
    def test_run_query_tool_empty_result(self, mock_get_db):
        """Test handling of empty query results"""
        mock_db = MagicMock()
        mock_db.run.return_value = ""
        mock_get_db.return_value = mock_db

        result = run_query_tool.invoke({"query": "SELECT * FROM empty_table"})

        assert "no results" in result.lower()

    @patch("src.chat_workflow.utils.tools.get_sql_database")
    def test_run_query_tool_database_error(self, mock_get_db):
        """Test handling of database errors"""
        mock_db = MagicMock()
        mock_db.run.side_effect = Exception("Connection failed")
        mock_get_db.return_value = mock_db

        result = run_query_tool.invoke({"query": "SELECT * FROM test"})

        assert "Error executing query" in result
        assert "Connection failed" in result


class TestExecuteQueryNode:
    """Test execute_query_node function"""

    @patch("src.chat_workflow.nodes.execute_query.run_query_tool")
    def test_execute_query_node_with_tool_call(self, mock_tool):
        """Test executing a query from tool call"""
        mock_tool.invoke.return_value = "Query result: 10 rows"

        # Create state with AIMessage containing tool call
        ai_message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "run_query_tool",
                    "args": {"query": "SELECT COUNT(*) FROM emails_processed"},
                    "id": "test_call_123",
                }
            ],
        )
        state = ChatState(messages=[ai_message])

        result = execute_query_node(state)

        # Verify tool was invoked
        mock_tool.invoke.assert_called_once()

        # Verify ToolMessage was created
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert "Query result" in result["messages"][0].content

        # Verify state updates
        assert "current_query" in result
        assert "query_result" in result

    def test_execute_query_node_no_tool_calls(self):
        """Test node when there are no tool calls"""
        state = ChatState(messages=[AIMessage(content="Hello")])

        result = execute_query_node(state)

        assert result == {"messages": []}

    def test_execute_query_node_empty_state(self):
        """Test node with empty state"""
        state = ChatState()

        result = execute_query_node(state)

        assert result == {"messages": []}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
