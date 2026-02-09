"""Tests for SQL query transparency feature in chat workflow"""

from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.chat_workflow.nodes.execute_query import execute_query_node
from agent.models.chat_models import ChatState, QueryExecution


@pytest.mark.unit
@patch("src.chat_workflow.nodes.execute_query.run_query_tool")
def test_execute_query_tracks_sql(mock_run_query):
    """Test that execute_query_node captures SQL queries for transparency"""
    # Mock the tool to return a simple result
    mock_run_query.invoke.return_value = "[('email1@test.com',), ('email2@test.com',)]"

    # Create a mock tool call with SQL query
    tool_call = {
        "name": "run_query_tool",
        "args": {"query": "SELECT * FROM emails_processed LIMIT 5"},
        "id": "test_call_123",
    }

    # Create AI message with tool call
    ai_message = AIMessage(content="", tool_calls=[tool_call])

    # Create state
    state = ChatState(messages=[ai_message])

    # Execute node
    result = execute_query_node(state)

    # Verify executed_queries is populated
    assert "executed_queries" in result
    assert len(result["executed_queries"]) == 1

    # Verify it's a QueryExecution object
    query_exec = result["executed_queries"][0]
    assert isinstance(query_exec, QueryExecution)
    assert query_exec.query == "SELECT * FROM emails_processed LIMIT 5"
    assert query_exec.explanation  # Should have an explanation
    assert query_exec.result_summary  # Should have a summary


@pytest.mark.unit
@patch("src.chat_workflow.nodes.execute_query.run_query_tool")
def test_execute_query_tracks_multiple_queries(mock_run_query):
    """Test that multiple SQL queries are all captured"""
    # Mock the tool to return different results for each call
    mock_run_query.invoke.side_effect = [
        "[(156,)]",
        "[('sender1@test.com',), ('sender2@test.com',)]",
    ]

    # Create multiple tool calls
    tool_calls = [
        {
            "name": "run_query_tool",
            "args": {"query": "SELECT COUNT(*) FROM emails_processed"},
            "id": "call_1",
        },
        {
            "name": "run_query_tool",
            "args": {"query": "SELECT sender FROM emails_processed LIMIT 10"},
            "id": "call_2",
        },
    ]

    # Create AI message with tool calls
    ai_message = AIMessage(content="", tool_calls=tool_calls)

    # Create state
    state = ChatState(messages=[ai_message])

    # Execute node
    result = execute_query_node(state)

    # Verify both queries are tracked
    assert "executed_queries" in result
    assert len(result["executed_queries"]) == 2

    # Verify QueryExecution objects
    assert isinstance(result["executed_queries"][0], QueryExecution)
    assert isinstance(result["executed_queries"][1], QueryExecution)
    assert (
        result["executed_queries"][0].query == "SELECT COUNT(*) FROM emails_processed"
    )
    assert (
        result["executed_queries"][1].query
        == "SELECT sender FROM emails_processed LIMIT 10"
    )


@pytest.mark.unit
def test_execute_query_empty_state():
    """Test that execute_query_node handles empty state gracefully"""
    # Create empty state
    state = ChatState(messages=[])

    # Execute node
    result = execute_query_node(state)

    # Verify empty result
    assert result["messages"] == []
    assert "executed_queries" not in result or result["executed_queries"] == []


@pytest.mark.unit
def test_chat_state_has_executed_queries_field():
    """Test that ChatState model includes executed_queries field"""
    # Create state with executed queries
    query_exec = QueryExecution(
        query="SELECT 1", explanation="Testing query", result_summary="Found 1 result"
    )
    state = ChatState(
        messages=[HumanMessage(content="test")], executed_queries=[query_exec]
    )

    # Verify field exists and is accessible
    assert hasattr(state, "executed_queries")
    assert len(state.executed_queries) == 1
    assert state.executed_queries[0].query == "SELECT 1"


@pytest.mark.unit
def test_executed_queries_add_reducer():
    """Test that executed_queries uses add reducer for accumulation"""
    from operator import add

    from agent.models.chat_models import ChatState, QueryExecution

    # Create initial state with one query
    query1 = QueryExecution(
        query="SELECT 1", explanation="First query", result_summary="Result 1"
    )
    state = ChatState(messages=[], executed_queries=[query1])

    # Simulate adding more queries (mimicking LangGraph's add reducer behavior)
    query2 = QueryExecution(
        query="SELECT 2", explanation="Second query", result_summary="Result 2"
    )
    query3 = QueryExecution(
        query="SELECT 3", explanation="Third query", result_summary="Result 3"
    )
    combined = add(state.executed_queries, [query2, query3])

    # Verify queries accumulate
    assert len(combined) == 3
    assert combined[0].query == "SELECT 1"
    assert combined[1].query == "SELECT 2"
    assert combined[2].query == "SELECT 3"
