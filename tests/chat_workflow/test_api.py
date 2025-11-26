"""Tests for FastAPI endpoints"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from server.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_graph():
    """Create mock graph for testing"""
    graph = MagicMock()
    return graph


class TestRootEndpoint:
    """Test root endpoint"""

    def test_root_returns_api_info(self, client):
        """Test root endpoint returns API information"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data
        assert "chat" in data["endpoints"]


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestChatEndpoint:
    """Test non-streaming chat endpoint"""

    @patch("src.chat_workflow.api.get_graph")
    def test_chat_success(self, mock_get_graph, client):
        """Test successful chat request"""
        # Mock graph
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [
                HumanMessage(content="How many emails?"),
                AIMessage(content="There are 147 emails in the database."),
            ]
        }
        mock_get_graph.return_value = mock_graph

        # Make request
        response = client.post(
            "/chat",
            json={
                "message": "How many emails are in the database?",
                "thread_id": "test-thread-123",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "147 emails" in data["response"]
        assert data["thread_id"] == "test-thread-123"

        # Verify graph was called correctly
        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args
        # Check positional args
        assert "messages" in call_args[0][0]
        # Check that config was passed (it's the second positional arg)
        assert len(call_args[0]) == 2 or call_args[1].get("config") is not None

    @patch("src.chat_workflow.api.get_graph")
    def test_chat_missing_message(self, mock_get_graph, client):
        """Test chat with missing message field"""
        response = client.post("/chat", json={"thread_id": "test-thread-123"})

        assert response.status_code == 422  # Validation error

    @patch("src.chat_workflow.api.get_graph")
    def test_chat_missing_thread_id(self, mock_get_graph, client):
        """Test chat with missing thread_id field"""
        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 422  # Validation error

    @patch("src.chat_workflow.api.get_graph")
    def test_chat_graph_error(self, mock_get_graph, client):
        """Test chat when graph raises exception"""
        # Mock graph to raise error
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = Exception("Database connection failed")
        mock_get_graph.return_value = mock_graph

        response = client.post(
            "/chat", json={"message": "Test message", "thread_id": "test-thread-123"}
        )

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()

    @patch("src.chat_workflow.api.get_graph")
    def test_chat_no_messages_in_result(self, mock_get_graph, client):
        """Test chat when graph returns no messages"""
        # Mock graph with empty messages
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"messages": []}
        mock_get_graph.return_value = mock_graph

        response = client.post(
            "/chat", json={"message": "Test message", "thread_id": "test-thread-123"}
        )

        assert response.status_code == 500
        assert "No response generated" in response.json()["detail"]


class TestHistoryEndpoint:
    """Test conversation history endpoint"""

    @patch("src.chat_workflow.api.get_graph")
    def test_get_history_success(self, mock_get_graph, client):
        """Test successful history retrieval"""
        # Mock state snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.config = {
            "configurable": {"checkpoint_id": "checkpoint-123", "thread_id": "test-thread"}
        }
        mock_snapshot.values = {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="Hi there!")]
        }
        mock_snapshot.created_at = "2025-11-19T10:00:00Z"
        mock_snapshot.metadata = {"step": 1}

        # Mock graph
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = [mock_snapshot]
        mock_get_graph.return_value = mock_graph

        # Make request
        response = client.get("/history/test-thread")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test-thread"
        assert "history" in data
        assert len(data["history"]) == 1
        assert data["history"][0]["checkpoint_id"] == "checkpoint-123"
        assert len(data["history"][0]["messages"]) == 2

    @patch("src.chat_workflow.api.get_graph")
    def test_get_history_empty(self, mock_get_graph, client):
        """Test history retrieval for thread with no history"""
        # Mock graph with empty history
        mock_graph = MagicMock()
        mock_graph.get_state_history.return_value = []
        mock_get_graph.return_value = mock_graph

        response = client.get("/history/nonexistent-thread")

        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "nonexistent-thread"
        assert data["history"] == []

    @patch("src.chat_workflow.api.get_graph")
    def test_get_history_error(self, mock_get_graph, client):
        """Test history retrieval when graph raises exception"""
        # Mock graph to raise error
        mock_graph = MagicMock()
        mock_graph.get_state_history.side_effect = Exception("Checkpointer error")
        mock_get_graph.return_value = mock_graph

        response = client.get("/history/test-thread")

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


class TestStreamEndpoint:
    """Test streaming chat endpoint"""

    @patch("src.chat_workflow.api.get_graph")
    def test_chat_stream_endpoint_exists(self, mock_get_graph, client):
        """Test that streaming endpoint exists and accepts requests"""
        # Mock graph with astream_events
        mock_graph = MagicMock()

        async def mock_astream_events(*args, **kwargs):
            """Mock async generator"""
            yield {
                "event": "on_chain_end",
                "data": {"output": {"messages": [AIMessage(content="Test response")]}},
            }

        mock_graph.astream_events = mock_astream_events
        mock_get_graph.return_value = mock_graph

        # Make request
        response = client.post(
            "/chat/stream", json={"message": "Test message", "thread_id": "test-thread-123"}
        )

        # Verify response starts streaming
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
