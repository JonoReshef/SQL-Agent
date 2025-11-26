"""Unit tests for FastAPI server"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.models.chat_models import QueryExecution, QueryExplanation
from src.server.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_graph():
    """Mock graph for testing"""
    graph = MagicMock()
    return graph


def test_root_endpoint(client):
    """Test root endpoint returns API information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "WestBrand SQL Chat Agent"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data
    assert "/chat" in data["endpoints"]["chat"]


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "westbrand-sql-chat-agent"


@patch("src.server.server.get_graph")
def test_chat_endpoint_success(mock_get_graph, client):
    """Test successful chat request"""
    # Mock graph response
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph

    # Create mock query execution with nested query_explanation
    query_execution = QueryExecution(
        query="SELECT COUNT(*) FROM emails_processed;",
        raw_result="156",
        query_explanation=QueryExplanation(
            description="Counts total emails", result_summary="Found 156 records"
        ),
    )

    # Mock graph invoke response
    mock_graph.invoke.return_value = {
        "messages": [AIMessage(content="There are 156 emails in the database.")],
        "executed_queries": [query_execution],
    }

    # Make request
    response = client.post(
        "/chat", json={"message": "How many emails are there?", "thread_id": "test-thread-123"}
    )

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "There are 156 emails in the database."
    assert data["thread_id"] == "test-thread-123"
    assert len(data["executed_queries"]) == 1
    assert data["executed_queries"][0]["query"] == "SELECT COUNT(*) FROM emails_processed;"
    assert data["executed_queries"][0]["explanation"] == "Counts total emails"
    assert data["executed_queries"][0]["result_summary"] == "Found 156 records"


@patch("src.server.server.get_graph")
def test_chat_endpoint_no_queries(mock_get_graph, client):
    """Test chat request with no executed queries"""
    # Mock graph response without queries
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph

    mock_graph.invoke.return_value = {
        "messages": [AIMessage(content="Hello! How can I help you?")],
        "executed_queries": [],
    }

    # Make request
    response = client.post("/chat", json={"message": "Hello", "thread_id": "test-thread-456"})

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Hello! How can I help you?"
    assert len(data["executed_queries"]) == 0


@patch("src.server.server.get_graph")
def test_chat_endpoint_no_response(mock_get_graph, client):
    """Test chat request that generates no response"""
    # Mock graph response with no messages
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph

    mock_graph.invoke.return_value = {
        "messages": [],
    }

    # Make request
    response = client.post("/chat", json={"message": "Test", "thread_id": "test-thread-789"})

    # Assert error response
    assert response.status_code == 500
    assert "No response generated" in response.json()["detail"]


@patch("src.server.server.get_graph")
def test_chat_endpoint_exception(mock_get_graph, client):
    """Test chat request with exception"""
    # Mock graph to raise exception
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph
    mock_graph.invoke.side_effect = Exception("Test error")

    # Make request
    response = client.post("/chat", json={"message": "Test", "thread_id": "test-thread-error"})

    # Assert error response
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]


@patch("src.server.server.get_graph")
def test_chat_endpoint_query_without_explanation(mock_get_graph, client):
    """Test chat request with query execution that has no explanation"""
    # Mock graph response
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph

    # Create mock query execution without query_explanation
    query_execution = QueryExecution(
        query="SELECT * FROM test;",
        raw_result="test result",
        query_explanation=None,  # No explanation
    )

    # Mock graph invoke response
    mock_graph.invoke.return_value = {
        "messages": [AIMessage(content="Query executed successfully.")],
        "executed_queries": [query_execution],
    }

    # Make request
    response = client.post(
        "/chat", json={"message": "Run query", "thread_id": "test-thread-no-explanation"}
    )

    # Assert response - should handle None query_explanation gracefully
    assert response.status_code == 200
    data = response.json()
    assert len(data["executed_queries"]) == 1
    # When query_explanation is None, fields should have defaults
    assert data["executed_queries"][0]["query"] == "SELECT * FROM test;"


@patch("src.server.server.get_graph")
def test_get_history_endpoint(mock_get_graph, client):
    """Test history retrieval endpoint"""
    # Mock graph with history
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph

    # Create mock state snapshots
    mock_snapshot = MagicMock()
    mock_snapshot.config = {"configurable": {"checkpoint_id": "checkpoint-1"}}
    mock_snapshot.values = {"messages": [AIMessage(content="Test message")]}
    mock_snapshot.created_at = "2025-11-20T10:00:00"
    mock_snapshot.metadata = {"test": "metadata"}

    mock_graph.get_state_history.return_value = [mock_snapshot]

    # Make request
    response = client.get("/history/test-thread-123")

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "test-thread-123"
    assert len(data["history"]) == 1
    assert data["history"][0]["checkpoint_id"] == "checkpoint-1"


@patch("src.server.server.get_graph")
def test_get_history_exception(mock_get_graph, client):
    """Test history endpoint with exception"""
    # Mock graph to raise exception
    mock_graph = MagicMock()
    mock_get_graph.return_value = mock_graph
    mock_graph.get_state_history.side_effect = Exception("History error")

    # Make request
    response = client.get("/history/test-thread-error")

    # Assert error response
    assert response.status_code == 500
    assert "History error" in response.json()["detail"]


def test_chat_endpoint_missing_fields(client):
    """Test chat request with missing required fields"""
    # Missing message field
    response = client.post("/chat", json={"thread_id": "test-thread"})
    assert response.status_code == 422  # Validation error

    # Missing thread_id field
    response = client.post("/chat", json={"message": "Test message"})
    assert response.status_code == 422  # Validation error
