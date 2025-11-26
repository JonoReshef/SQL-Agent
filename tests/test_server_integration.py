"""Integration tests for FastAPI server with actual workflow"""

import pytest
from fastapi.testclient import TestClient

from src.server.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.mark.integration
def test_chat_endpoint_real_workflow(client):
    """Test chat endpoint with real workflow execution"""
    # Make a simple database query
    response = client.post(
        "/chat",
        json={"message": "How many emails are in the system?", "thread_id": "integration-test-123"},
    )

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "response" in data
    assert "thread_id" in data
    assert "executed_queries" in data
    assert data["thread_id"] == "integration-test-123"

    # Response should contain some content
    assert len(data["response"]) > 0

    # Should have executed at least one query
    assert len(data["executed_queries"]) > 0

    # Check query execution structure
    for query_exec in data["executed_queries"]:
        assert "query" in query_exec
        assert "explanation" in query_exec
        assert "result_summary" in query_exec
        # Query should be a SELECT statement
        assert "SELECT" in query_exec["query"].upper()
        # Explanation should be non-empty
        assert len(query_exec["explanation"]) > 0


@pytest.mark.integration
def test_chat_endpoint_follow_up_question(client):
    """Test chat endpoint with follow-up questions in same thread"""
    thread_id = "integration-test-follow-up"

    # First question - simple count
    response1 = client.post(
        "/chat", json={"message": "How many emails are in the database?", "thread_id": thread_id}
    )
    assert response1.status_code == 200, f"First request failed: {response1.json()}"
    data1 = response1.json()
    assert len(data1["executed_queries"]) > 0

    # Follow-up question - simple list (should maintain context)
    response2 = client.post(
        "/chat", json={"message": "What tables are available?", "thread_id": thread_id}
    )
    assert response2.status_code == 200, f"Second request failed: {response2.json()}"
    data2 = response2.json()
    # This might not need queries if it uses cached schema info
    assert len(data2["response"]) > 0


@pytest.mark.integration
def test_get_history_real_thread(client):
    """Test history endpoint with real conversation"""
    thread_id = "integration-test-history"

    # Create some conversation history
    client.post("/chat", json={"message": "How many emails are there?", "thread_id": thread_id})

    # Retrieve history
    response = client.get(f"/history/{thread_id}")
    assert response.status_code == 200
    data = response.json()

    # Check history structure
    assert data["thread_id"] == thread_id
    assert "history" in data
    assert len(data["history"]) > 0

    # Check history entries
    for entry in data["history"]:
        assert "messages" in entry
        assert "timestamp" in entry


@pytest.mark.integration
def test_chat_endpoint_complex_query(client):
    """Test chat endpoint with a more complex query"""
    response = client.post(
        "/chat",
        json={
            "message": "What are the unique requestors in the system?",
            "thread_id": "integration-test-complex",
        },
    )

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Should have response
    assert len(data["response"]) > 0

    # Check queries were executed with explanations
    assert len(data["executed_queries"]) > 0
    for query_exec in data["executed_queries"]:
        assert len(query_exec["query"]) > 0
        assert len(query_exec["explanation"]) > 0
        # Result summary might be None in some cases
        if query_exec["result_summary"]:
            assert len(query_exec["result_summary"]) > 0
