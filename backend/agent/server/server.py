"""FastAPI server for SQL chat agent"""

import asyncio
import json
import queue
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage

from agent.chat_workflow.graph import create_chat_graph
from agent.database.connection import get_db_session, get_engine
from agent.database.models import ChatMessageRecord, ChatThread, create_all_tables
from agent.models.chat_models import ChatState
from agent.models.server import (
    BulkImportRequest,
    ChatMessageModel,
    ChatRequest,
    ChatResponse,
    CheckpointData,
    CreateThreadRequest,
    HistoryResponse,
    MessageHistory,
    QueryExecutionResponse,
    SaveMessageRequest,
    ThreadListResponse,
    ThreadResponse,
    UpdateMessageRequest,
    UpdateThreadRequest,
)


# Queue event types for stream worker → SSE generator communication
@dataclass
class StreamEvent:
    """A pre-formatted SSE string to forward to the client."""

    sse_data: str


@dataclass
class StreamEnd:
    """Sentinel: stream complete, DB finalized."""

    pass


@dataclass
class StreamError:
    """Sentinel: error occurred, DB finalized."""

    sse_data: str


# Reusable thread pool for stream workers
_stream_executor = ThreadPoolExecutor(
    max_workers=10, thread_name_prefix="stream-worker"
)


# Initialize FastAPI app
app = FastAPI(
    title="WestBrand SQL Chat Agent",
    description="Natural language interface to WestBrand database",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize graph (singleton)
_graph = None


def get_graph():
    """Get or create graph instance (singleton pattern)"""
    global _graph
    if _graph is None:
        _graph = create_chat_graph()
    return _graph


def extract_title(text: str, max_length: int = 50) -> str:
    """Extract first meaningful sentence from text for thread title."""
    cleaned = text.strip()
    cleaned = " ".join(cleaned.split())
    import re

    match = re.match(r"^[^.!?]+[.!?]", cleaned)
    first_sentence = match.group(0) if match else cleaned
    if len(first_sentence) <= max_length:
        return first_sentence
    return first_sentence[: max_length - 3] + "..."


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "WestBrand SQL Chat Agent",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "chat_stream": "/chat/stream",
            "history": "/history/{thread_id}",
            "threads": "/threads",
            "thread_messages": "/threads/{thread_id}/messages",
            "threads_import": "/threads/import",
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Non-streaming chat endpoint.

    Processes a user message and returns the complete response.

    Args:
        request: ChatRequest with message and thread_id

    Returns:
        ChatResponse with agent's answer

    Raises:
        HTTPException: If graph execution fails
    """
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": request.thread_id}}

        # Invoke graph with user message and complexity setting
        result = graph.invoke(
            {
                "messages": [HumanMessage(content=request.message)],
                "anticipate_complexity": request.anticipate_complexity,
            },
            config,  # type: ignore
        )

        # Extract final message
        if not result.get("messages"):
            raise HTTPException(status_code=500, detail="No response generated")

        final_message = result["messages"][-1]
        response_content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        # Extract executed queries for transparency
        executed_queries_raw = result.get("executed_queries", [])
        executed_queries = [
            QueryExecutionResponse(
                query=qe.query,
                explanation=(
                    qe.query_explanation.description
                    if qe.query_explanation
                    else "No explanation available"
                ),
                result_summary=(
                    qe.query_explanation.result_summary
                    if qe.query_explanation
                    else "No result summary available"
                ),
            )
            for qe in executed_queries_raw
        ]

        return ChatResponse(
            response=response_content,
            thread_id=request.thread_id,
            executed_queries=executed_queries,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


def _stream_worker(q: queue.Queue, request: ChatRequest) -> None:  # type: ignore[type-arg]
    """
    Run LLM streaming + DB persistence in a background thread.

    Pushes SSE-formatted events into `q`. Always finalizes the DB,
    even if the SSE client disconnects mid-stream.
    """
    assistant_message_id: str | None = None
    full_response = ""
    queries_payload: list[dict[str, Any]] | None = None
    summary_payload: str | None = None

    try:
        print(
            f"Starting stream for thread: {request.thread_id}, message: {request.message[:50]}...",
            flush=True,
        )

        # Validate request
        if not request.message or not request.message.strip():
            raise ValueError("Message cannot be empty")

        graph = get_graph()
        print("Graph retrieved successfully", flush=True)

        config = {"configurable": {"thread_id": request.thread_id}}

        # ── Persist user message BEFORE streaming ──
        user_message_id = str(uuid.uuid4())
        thread_title: str | None = None

        with get_db_session() as session:
            # Auto-create thread if it doesn't exist
            thread = session.get(ChatThread, request.thread_id)
            if not thread:
                thread = ChatThread(id=request.thread_id, title="New Chat")
                session.add(thread)
                session.flush()

            # Insert user message
            user_msg = ChatMessageRecord(
                id=user_message_id,
                thread_id=request.thread_id,
                role="user",
                content=request.message,
                status="complete",
            )
            session.add(user_msg)

            # Update thread metadata
            current_count = cast("int | None", thread.message_count) or 0
            thread.message_count = current_count + 1  # type: ignore[assignment]
            thread.last_message = request.message  # type: ignore[assignment]

            # Auto-title if still "New Chat"
            if cast(str, thread.title) == "New Chat":
                thread_title = extract_title(request.message)
                thread.title = thread_title  # type: ignore[assignment]

        # Emit user_message_created event
        q.put(
            StreamEvent(
                sse_data=f"data: {json.dumps({'type': 'user_message_created', 'message_id': user_message_id, 'thread_title': thread_title})}\n\n"
            )
        )

        # ── Persist assistant placeholder BEFORE streaming ──
        assistant_message_id = str(uuid.uuid4())

        with get_db_session() as session:
            assistant_msg = ChatMessageRecord(
                id=assistant_message_id,
                thread_id=request.thread_id,
                role="assistant",
                content="",
                status="streaming",
            )
            session.add(assistant_msg)

            thread = session.get(ChatThread, request.thread_id)
            if thread:
                current_count = cast("int | None", thread.message_count) or 0
                thread.message_count = current_count + 1  # type: ignore[assignment]

        # Emit assistant_message_created event
        q.put(
            StreamEvent(
                sse_data=f"data: {json.dumps({'type': 'assistant_message_created', 'message_id': assistant_message_id})}\n\n"
            )
        )

        # ── Stream LLM response ──
        print("Starting stream...", flush=True)
        last_event = None

        # Initial status event
        q.put(
            StreamEvent(
                sse_data=f"data: {json.dumps({'type': 'status', 'content': 'Initiating workflow'})}\n\n"
            )
        )

        for stream_mode, event in graph.stream(
            {
                "user_question": request.message,
                "anticipate_complexity": request.anticipate_complexity,
            },
            config,  # type: ignore
            stream_mode=["values", "messages"],
        ):
            # Handle complete state updates
            if stream_mode == "values":
                event_update = ChatState.model_validate(event)
                last_event = event_update

                if "status_update" in event and event_update.status_update:
                    q.put(
                        StreamEvent(
                            sse_data=f"data: {json.dumps({'type': 'status', 'content': event_update.status_update})}\n\n"
                        )
                    )

            elif stream_mode == "messages":
                message_chunk: AIMessageChunk = (
                    event[0] if isinstance(event, tuple) else event
                )  # type: ignore
                metadata = (
                    event[1] if isinstance(event, tuple) and len(event) > 1 else {}
                )

                node_name = metadata.get("langgraph_node", "")
                if node_name == "generate_query":
                    if hasattr(message_chunk, "content") and message_chunk.content:
                        token = str(message_chunk.content)
                        if token:
                            full_response += token
                            q.put(
                                StreamEvent(
                                    sse_data=f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                                )
                            )

        # ── Finalize assistant message AFTER streaming ──
        if last_event:
            if last_event.executed_queries_enriched:
                queries_payload = []
                for qe in last_event.executed_queries_enriched:
                    queries_payload.append(
                        {
                            "query": qe.query,
                            "explanation": (
                                qe.query_explanation.description
                                if qe.query_explanation
                                else "No explanation available"
                            ),
                            "result_summary": (
                                qe.query_explanation.result_summary
                                if qe.query_explanation
                                else "No result summary available"
                            ),
                        }
                    )
                q.put(
                    StreamEvent(
                        sse_data=f"data: {json.dumps({'type': 'queries', 'queries': queries_payload})}\n\n"
                    )
                )

            if last_event.overall_summary:
                summary_payload = last_event.overall_summary
                q.put(
                    StreamEvent(
                        sse_data=f"data: {json.dumps({'type': 'summary', 'content': summary_payload})}\n\n"
                    )
                )

            # Fallback: If no tokens were streamed but there's a final message
            if not full_response and last_event.messages:
                last_message = last_event.messages[-1]
                if (
                    hasattr(last_message, "content")
                    and last_message.content
                    and last_message.__class__.__name__ == "AIMessage"
                ):
                    full_response = str(last_message.content)
                    q.put(
                        StreamEvent(
                            sse_data=f"data: {json.dumps({'type': 'message', 'content': full_response})}\n\n"
                        )
                    )

        # Send end event
        q.put(StreamEvent(sse_data=f"data: {json.dumps({'type': 'end'})}\n\n"))
        q.put(StreamEnd())

    except Exception as e:
        error_message = (
            str(e) if str(e) else "An unexpected error occurred during streaming"
        )
        error_type = type(e).__name__
        print(f"Stream error ({error_type}): {error_message}", flush=True)
        import traceback

        traceback.print_exc()

        error_data = json.dumps({"type": "error", "content": error_message})
        q.put(StreamEvent(sse_data=f"data: {error_data}\n\n"))
        q.put(StreamError(sse_data=f"data: {error_data}\n\n"))

    finally:
        # ── DB finalization always runs, even if client disconnected ──
        if assistant_message_id:
            try:
                with get_db_session() as session:
                    assistant_record = session.get(
                        ChatMessageRecord, assistant_message_id
                    )
                    if assistant_record:
                        assistant_record.content = full_response  # type: ignore[assignment]
                        assistant_record.status = "complete"  # type: ignore[assignment]
                        if queries_payload:
                            assistant_record.queries = queries_payload  # type: ignore[assignment]
                        if summary_payload:
                            assistant_record.overall_summary = summary_payload  # type: ignore[assignment]

                    thread = session.get(ChatThread, request.thread_id)
                    if thread and full_response:
                        truncated = (
                            full_response[:200] + "..."
                            if len(full_response) > 200
                            else full_response
                        )
                        thread.last_message = truncated  # type: ignore[assignment]
            except Exception as db_err:
                print(f"DB finalization error: {db_err}", flush=True)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    LLM execution and DB persistence run in a background thread that always
    completes, even if the SSE client disconnects. The SSE generator is a
    thin consumer that reads from a queue.
    """
    q: queue.Queue = queue.Queue()  # type: ignore[type-arg]
    future = _stream_executor.submit(_stream_worker, q, request)

    async def sse_generator():
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    item = await loop.run_in_executor(None, lambda: q.get(timeout=0.1))
                except queue.Empty:
                    if future.done():
                        # Worker finished and queue is drained
                        break
                    await asyncio.sleep(0)
                    continue

                if isinstance(item, (StreamEnd, StreamError)):
                    break
                yield item.sse_data
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass  # Client disconnected — worker keeps running to completion

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@app.get("/history/{thread_id}", response_model=HistoryResponse)
async def get_history(thread_id: str) -> HistoryResponse:
    """
    Get conversation history for a thread.

    Retrieves all checkpoints and messages for the specified thread.

    Args:
        thread_id: Thread identifier

    Returns:
        HistoryResponse with conversation history

    Raises:
        HTTPException: If history retrieval fails
    """
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}

        # Get state history from checkpointer
        history = []
        for state_snapshot in graph.get_state_history(config):  # type: ignore
            checkpoint_config = state_snapshot.config.get("configurable", {})  # type: ignore

            # Convert messages to MessageHistory objects
            messages = [
                MessageHistory(
                    type=msg.__class__.__name__,
                    content=msg.content if hasattr(msg, "content") else str(msg),
                )
                for msg in state_snapshot.values.get("messages", [])
            ]

            # Create CheckpointData object
            # Convert metadata to dict (handle CheckpointMetadata or dict types)
            metadata_dict: dict[str, Any] = {}
            if state_snapshot.metadata:
                try:
                    # Try to convert to dict if it's a CheckpointMetadata object
                    if hasattr(state_snapshot.metadata, "__dict__"):
                        metadata_dict = dict(vars(state_snapshot.metadata))
                    elif isinstance(state_snapshot.metadata, dict):
                        metadata_dict = dict(state_snapshot.metadata)
                except Exception:
                    # Fallback to empty dict if conversion fails
                    pass

            checkpoint_data = CheckpointData(
                checkpoint_id=checkpoint_config.get("checkpoint_id", "unknown"),
                messages=messages,
                timestamp=str(state_snapshot.created_at)
                if state_snapshot.created_at
                else None,
                metadata=metadata_dict,
            )
            history.append(checkpoint_data)

        return HistoryResponse(thread_id=thread_id, history=history)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving history: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "westbrand-sql-chat-agent"}


# ============================================================================
# Startup: ensure chat tables exist
# ============================================================================


@app.on_event("startup")
async def startup_create_chat_tables():
    """Create chat_threads and chat_messages tables if they don't exist"""
    engine = get_engine()
    create_all_tables(engine)


@app.on_event("startup")
async def cleanup_stale_streaming_messages():
    """Mark any orphaned 'streaming' messages as complete on server start."""
    with get_db_session() as session:
        stale = (
            session.query(ChatMessageRecord)
            .filter(ChatMessageRecord.status == "streaming")
            .all()
        )
        for msg in stale:
            msg.status = "complete"  # type: ignore[assignment]
            if not cast(str, msg.content):
                msg.content = "[Response interrupted]"  # type: ignore[assignment]
        if stale:
            print(f"Cleaned up {len(stale)} stale streaming message(s)", flush=True)


@app.on_event("shutdown")
async def shutdown_stream_executor():
    """Drain the stream worker thread pool on shutdown."""
    _stream_executor.shutdown(wait=True)


# ============================================================================
# Thread CRUD Endpoints
# ============================================================================


def _thread_to_response(thread: ChatThread) -> ThreadResponse:
    """Convert a ChatThread ORM object to a ThreadResponse"""
    thread_id = cast(str, thread.id)
    title = cast(str, thread.title)
    last_message = cast("str | None", thread.last_message) or ""
    updated_at = cast("datetime | None", thread.updated_at)
    created_at = cast(datetime, thread.created_at)
    message_count = cast("int | None", thread.message_count) or 0
    ts = updated_at.isoformat() if updated_at else created_at.isoformat()
    return ThreadResponse(
        id=thread_id,
        title=title,
        last_message=last_message,
        timestamp=ts,
        message_count=message_count,
    )


@app.get("/threads", response_model=ThreadListResponse)
async def list_threads():
    """List all chat threads, most recent first"""
    with get_db_session() as session:
        threads = session.query(ChatThread).order_by(ChatThread.updated_at.desc()).all()
        return ThreadListResponse(threads=[_thread_to_response(t) for t in threads])


@app.post("/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(request: CreateThreadRequest):
    """Create a new chat thread"""
    with get_db_session() as session:
        existing = session.get(ChatThread, request.id)
        if existing:
            return _thread_to_response(existing)

        thread = ChatThread(
            id=request.id,
            title=request.title,
        )
        session.add(thread)
        session.flush()
        return _thread_to_response(thread)


@app.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(thread_id: str, request: UpdateThreadRequest):
    """Update a chat thread's metadata"""
    with get_db_session() as session:
        thread = session.get(ChatThread, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        if request.title is not None:
            thread.title = request.title  # type: ignore[assignment]
        if request.last_message is not None:
            thread.last_message = request.last_message  # type: ignore[assignment]
        if request.message_count is not None:
            thread.message_count = request.message_count  # type: ignore[assignment]

        session.flush()
        return _thread_to_response(thread)


@app.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str):
    """Delete a chat thread and all its messages"""
    with get_db_session() as session:
        thread = session.get(ChatThread, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        session.delete(thread)


@app.delete("/threads", status_code=204)
async def delete_all_threads():
    """Delete all chat threads and messages"""
    with get_db_session() as session:
        session.query(ChatMessageRecord).delete()
        session.query(ChatThread).delete()


# ============================================================================
# Message CRUD Endpoints
# ============================================================================


def _message_to_model(msg: ChatMessageRecord) -> ChatMessageModel:
    """Convert a ChatMessageRecord ORM object to a ChatMessageModel"""
    msg_id = cast(str, msg.id)
    role = cast(str, msg.role)
    content = cast("str | None", msg.content) or ""
    created_at = cast("datetime | None", msg.created_at)
    ts = (
        created_at.isoformat() if created_at else datetime.now(timezone.utc).isoformat()
    )
    status = cast("str | None", msg.status)
    queries = cast("list[dict[str, Any]] | None", msg.queries)
    overall_summary = cast("str | None", msg.overall_summary)
    return ChatMessageModel(
        id=msg_id,
        role=role,
        content=content,
        timestamp=ts,
        status=status,
        queries=queries,
        overall_summary=overall_summary,
    )


@app.get("/threads/{thread_id}/messages", response_model=list[ChatMessageModel])
async def list_messages(thread_id: str):
    """List all messages for a thread, ordered by creation time"""
    with get_db_session() as session:
        thread = session.get(ChatThread, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        messages = (
            session.query(ChatMessageRecord)
            .filter(ChatMessageRecord.thread_id == thread_id)
            .order_by(ChatMessageRecord.created_at)
            .all()
        )
        return [_message_to_model(m) for m in messages]


@app.post(
    "/threads/{thread_id}/messages", response_model=ChatMessageModel, status_code=201
)
async def save_message(thread_id: str, request: SaveMessageRequest):
    """Save a new message to a thread"""
    with get_db_session() as session:
        thread = session.get(ChatThread, thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Check if message already exists (idempotent)
        existing = session.get(ChatMessageRecord, request.id)
        if existing:
            return _message_to_model(existing)

        created_at = (
            datetime.fromisoformat(request.timestamp)
            if request.timestamp
            else datetime.now(timezone.utc)
        )
        msg = ChatMessageRecord(
            id=request.id,
            thread_id=thread_id,
            role=request.role,
            content=request.content,
            status=request.status,
            queries=request.queries,
            overall_summary=request.overall_summary,
            created_at=created_at,
        )
        session.add(msg)

        # Update thread metadata
        thread.last_message = request.content  # type: ignore[assignment]
        thread.message_count = (cast("int | None", thread.message_count) or 0) + 1  # type: ignore[assignment]

        session.flush()
        return _message_to_model(msg)


@app.patch(
    "/threads/{thread_id}/messages/{message_id}", response_model=ChatMessageModel
)
async def update_message(
    thread_id: str, message_id: str, request: UpdateMessageRequest
):
    """Update an existing message (e.g., after streaming completes)"""
    with get_db_session() as session:
        msg = session.get(ChatMessageRecord, message_id)
        if not msg or cast(str, msg.thread_id) != thread_id:
            raise HTTPException(status_code=404, detail="Message not found")

        if request.content is not None:
            msg.content = request.content  # type: ignore[assignment]
        if request.status is not None:
            msg.status = request.status  # type: ignore[assignment]
        if request.queries is not None:
            msg.queries = request.queries  # type: ignore[assignment]
        if request.overall_summary is not None:
            msg.overall_summary = request.overall_summary  # type: ignore[assignment]

        # Update thread's last_message if content changed
        if request.content is not None:
            thread = session.get(ChatThread, thread_id)
            if thread:
                thread.last_message = request.content  # type: ignore[assignment]

        session.flush()
        return _message_to_model(msg)


# ============================================================================
# Bulk Import (for localStorage migration)
# ============================================================================


@app.post("/threads/import", status_code=201)
async def bulk_import(request: BulkImportRequest):
    """Import threads and messages from localStorage in bulk"""
    imported_threads = 0
    imported_messages = 0

    with get_db_session() as session:
        for thread_req in request.threads:
            existing = session.get(ChatThread, thread_req.id)
            if not existing:
                thread = ChatThread(
                    id=thread_req.id,
                    title=thread_req.title,
                )
                session.add(thread)
                imported_threads += 1

        session.flush()

        for thread_id, msgs in request.messages.items():
            thread = session.get(ChatThread, thread_id)
            if not thread:
                continue

            for msg_req in msgs:
                existing_msg = session.get(ChatMessageRecord, msg_req.id)
                if existing_msg:
                    continue

                created_at = (
                    datetime.fromisoformat(msg_req.timestamp)
                    if msg_req.timestamp
                    else datetime.now(timezone.utc)
                )
                msg = ChatMessageRecord(
                    id=msg_req.id,
                    thread_id=thread_id,
                    role=msg_req.role,
                    content=msg_req.content,
                    status=msg_req.status,
                    queries=msg_req.queries,
                    overall_summary=msg_req.overall_summary,
                    created_at=created_at,
                )
                session.add(msg)
                imported_messages += 1

            # Update thread metadata
            if thread:
                thread.message_count = (  # type: ignore[assignment]
                    session.query(ChatMessageRecord)
                    .filter(ChatMessageRecord.thread_id == thread_id)
                    .count()
                )
                last_msg = (
                    session.query(ChatMessageRecord)
                    .filter(ChatMessageRecord.thread_id == thread_id)
                    .order_by(ChatMessageRecord.created_at.desc())
                    .first()
                )
                if last_msg:
                    thread.last_message = cast(str, last_msg.content)  # type: ignore[assignment]

    return {
        "imported_threads": imported_threads,
        "imported_messages": imported_messages,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
