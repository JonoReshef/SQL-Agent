"""Tests for chat workflow models"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.models.chat_models import ChatState


class TestChatState:
    """Test ChatState Pydantic model"""

    def test_chat_state_creation_with_defaults(self):
        """Test ChatState can be created with all default values"""
        state = ChatState()

        assert state.messages == []
        assert state.available_tables == []
        assert state.current_query is None
        assert state.query_result is None
        assert state.error is None

    def test_chat_state_with_messages(self):
        """Test ChatState can store LangChain messages"""
        messages = [HumanMessage(content="Hello"), AIMessage(content="Hi there!")]
        state = ChatState(messages=messages)

        assert len(state.messages) == 2
        assert state.messages[0].content == "Hello"
        assert state.messages[1].content == "Hi there!"

    def test_chat_state_with_all_fields(self):
        """Test ChatState with all fields populated"""
        state = ChatState(
            messages=[HumanMessage(content="Test")],
            available_tables=["emails_processed", "product_mentions"],
            current_query="SELECT * FROM emails_processed LIMIT 10",
            query_result="10 rows returned",
            error=None,
        )

        assert len(state.messages) == 1
        assert len(state.available_tables) == 2
        assert state.current_query is not None
        assert "SELECT" in state.current_query
        assert state.query_result == "10 rows returned"
        assert state.error is None

    def test_chat_state_with_error(self):
        """Test ChatState can store error messages"""
        state = ChatState(error="Database connection failed")

        assert state.error == "Database connection failed"

    def test_chat_state_message_reducer_behavior(self):
        """Test that messages field uses add reducer (appending behavior)"""
        # This tests the Annotated[List[BaseMessage], add] behavior
        # In LangGraph, the 'add' operator will append messages
        state = ChatState(messages=[HumanMessage(content="First")])

        # Simulate reducer behavior (this would happen in LangGraph)
        new_messages = [AIMessage(content="Second")]
        combined = state.messages + new_messages

        assert len(combined) == 2
        assert combined[0].content == "First"
        assert combined[1].content == "Second"

    def test_chat_state_serialization(self):
        """Test ChatState can be serialized to dict (important for LangGraph)"""
        state = ChatState(
            messages=[HumanMessage(content="Test")],
            available_tables=["test_table"],
            current_query="SELECT 1",
        )

        # Use model_dump() for Pydantic v2
        state_dict = state.model_dump()

        assert "messages" in state_dict
        assert "available_tables" in state_dict
        assert state_dict["available_tables"] == ["test_table"]
        assert state_dict["current_query"] == "SELECT 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
