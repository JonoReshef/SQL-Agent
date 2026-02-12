"""Test data generators matching exact Pydantic schemas from agent.models.server."""

import uuid
from datetime import datetime, timezone


def _prefixed_uuid() -> str:
    """Generate a 36-char ID with 'lt-' prefix (fits String(36) columns)."""
    raw = uuid.uuid4().hex  # 32 hex chars, no dashes
    return f"lt-{raw[:33]}"


def make_thread_id() -> str:
    return _prefixed_uuid()


def make_create_thread_payload(thread_id: str | None = None) -> dict:
    """Matches CreateThreadRequest: {id: str, title: str}"""
    return {
        "id": thread_id or make_thread_id(),
        "title": "Load Test Thread",
    }


def make_save_message_payload(thread_id: str) -> dict:
    """Matches SaveMessageRequest: {id, role, content, timestamp, status?}"""
    return {
        "id": _prefixed_uuid(),
        "role": "user",
        "content": "Load test message content",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
    }


def make_chat_request(thread_id: str) -> dict:
    """Matches ChatRequest: {message, thread_id, anticipate_complexity?}"""
    return {
        "message": "What are the top 5 products by revenue?",
        "thread_id": thread_id,
        "anticipate_complexity": False,
    }


def make_update_thread_payload() -> dict:
    """Matches UpdateThreadRequest: {title?, last_message?, message_count?}"""
    return {"title": f"Updated {datetime.now(timezone.utc).isoformat()[:19]}"}
