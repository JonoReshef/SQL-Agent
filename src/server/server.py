"""FastAPI server for SQL chat agent"""

import json
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.chat_workflow.graph import create_chat_graph

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


# Request/Response models
class QueryExecutionResponse(BaseModel):
    """Response model for query execution details"""

    query: str = Field(..., description="The SQL query that was executed")
    explanation: str = Field(..., description="Human-readable explanation of what the query does")
    result_summary: str = Field(..., description="Brief summary of the query results")


class ChatRequest(BaseModel):
    """Request model for chat endpoints"""

    message: str = Field(..., description="User's question or message")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response model for non-streaming chat endpoint"""

    response: str = Field(..., description="Agent's response")
    thread_id: str = Field(..., description="Thread ID for this conversation")
    executed_queries: list[QueryExecutionResponse] = Field(
        default_factory=list, description="SQL queries executed with explanations and summaries"
    )


class HistoryResponse(BaseModel):
    """Response model for history endpoint"""

    thread_id: str = Field(..., description="Thread ID")
    history: list = Field(..., description="List of checkpoint states")


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

        # Invoke graph with user message
        result = graph.invoke(
            {"messages": [HumanMessage(content=request.message)]},
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
                query=qe.query, explanation=qe.explanation, result_summary=qe.result_summary
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

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from graph stream"""
        try:
            graph = get_graph()
            config = {"configurable": {"thread_id": request.thread_id}}

            executed_queries = []

            # Stream events from graph
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=request.message)]},
                config,  # type: ignore
                version="v2",
            ):
                # Stream LLM tokens
                if event["event"] == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

                # Stream node completions
                elif event["event"] == "on_chain_end":
                    output_data = event.get("data", {})
                    if "output" in output_data:  # type: ignore
                        output = output_data["output"]  # type: ignore
                        if isinstance(output, dict):
                            # Collect executed queries
                            if "executed_queries" in output:
                                for qe in output["executed_queries"]:
                                    executed_queries.append(
                                        {
                                            "query": qe.query,
                                            "explanation": qe.explanation,
                                            "result_summary": qe.result_summary,
                                        }
                                    )

                            # Stream messages
                            if "messages" in output:
                                last_message = output["messages"][-1]
                                if hasattr(last_message, "content"):
                                    yield f"data: {json.dumps({'type': 'message', 'content': last_message.content})}\n\n"

            # Send executed queries before end event for transparency
            if executed_queries:
                yield f"data: {json.dumps({'type': 'queries', 'queries': executed_queries})}\n\n"

            # Send end event
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:
            error_data = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
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
            checkpoint_data = {
                "checkpoint_id": checkpoint_config.get("checkpoint_id", "unknown"),
                "messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": msg.content if hasattr(msg, "content") else str(msg),
                    }
                    for msg in state_snapshot.values.get("messages", [])
                ],
                "timestamp": str(state_snapshot.created_at) if state_snapshot.created_at else None,
                "metadata": state_snapshot.metadata,
            }
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
