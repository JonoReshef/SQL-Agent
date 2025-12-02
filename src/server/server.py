"""FastAPI server for SQL chat agent"""

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage

from src.chat_workflow.graph import create_chat_graph
from src.models.chat_models import ChatState
from src.models.server import (
    ChatRequest,
    ChatResponse,
    CheckpointData,
    HistoryResponse,
    MessageHistory,
    QueryExecutionResponse,
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
            final_message.content if hasattr(final_message, "content") else str(final_message)
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
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Streams tokens and events in real-time as the agent processes the request.

    Args:
        request: ChatRequest with message and thread_id

    Returns:
        StreamingResponse with SSE events
    """
    import asyncio

    def sync_event_generator():
        """Generate SSE events from graph stream (synchronous)"""
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

            # Use synchronous stream with multiple modes:
            # - "values": Complete state updates (status, queries, summary)
            # - "messages": Token-by-token streaming from LLM
            print("Starting stream...", flush=True)
            last_event = None
            full_response = ""  # Fallback accumulator

            # Initial status event
            yield f"data: {json.dumps({'type': 'status', 'content': 'Initiating workflow'})}\n\n"

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
                    # When we have a values update we are returned the full state
                    event_update = ChatState.model_validate(event)

                    # Store last event for final summary
                    last_event = event_update

                    # Send status updates to frontend
                    if "status_update" in event and event_update.status_update:
                        yield f"data: {json.dumps({'type': 'status', 'content': event_update.status_update})}\n\n"

                elif stream_mode == "messages":
                    # Handle token-by-token streaming
                    # Event is a tuple: (message_chunk, metadata)
                    message_chunk: AIMessageChunk = event[0] if isinstance(event, tuple) else event  # type: ignore
                    metadata = event[1] if isinstance(event, tuple) and len(event) > 1 else {}

                    # Only stream tokens from generate_query node
                    node_name = metadata.get("langgraph_node", "")
                    if node_name == "generate_query":
                        # Check for content attribute (text tokens)
                        if hasattr(message_chunk, "content") and message_chunk.content:
                            token = str(message_chunk.content)
                            if token:
                                full_response += token
                                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # After stream completes, send queries and summary from last event
            if last_event:
                # Send executed queries before end event for transparency
                if last_event.executed_queries_enriched:
                    # Store only the last executed queries for final transparency
                    executed_queries = []
                    for qe in last_event.executed_queries_enriched:
                        executed_queries.append(
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

                    yield f"data: {json.dumps({'type': 'queries', 'queries': executed_queries})}\n\n"

                # Send overall summary if available
                if last_event.overall_summary:
                    yield f"data: {json.dumps({'type': 'summary', 'content': last_event.overall_summary})}\n\n"

                # Fallback: If no tokens were streamed but there's a final message, send it
                if not full_response and last_event.messages:
                    last_message = last_event.messages[-1]
                    if (
                        hasattr(last_message, "content")
                        and last_message.content
                        and last_message.__class__.__name__ == "AIMessage"
                    ):
                        yield f"data: {json.dumps({'type': 'message', 'content': last_message.content})}\n\n"

            # Send end event
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:
            error_message = str(e) if str(e) else "An unexpected error occurred during streaming"
            error_type = type(e).__name__
            print(f"Stream error ({error_type}): {error_message}", flush=True)
            import traceback

            traceback.print_exc()
            error_data = json.dumps({"type": "error", "content": error_message})
            yield f"data: {error_data}\n\n"

    async def async_wrapper():
        """Wrap synchronous generator in async context"""
        for chunk in sync_event_generator():
            yield chunk
            # Small yield to prevent blocking
            await asyncio.sleep(0)

    return StreamingResponse(
        async_wrapper(),
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
                timestamp=str(state_snapshot.created_at) if state_snapshot.created_at else None,
                metadata=metadata_dict,
            )
            history.append(checkpoint_data)

        return HistoryResponse(thread_id=thread_id, history=history)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "westbrand-sql-chat-agent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
