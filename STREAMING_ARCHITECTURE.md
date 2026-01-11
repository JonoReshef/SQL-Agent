# WestBrand Streaming Chat Architecture

## Overview

This document describes the **token-by-token streaming architecture** with **client-side buffering** for smooth, real-time response rendering in the WestBrand SQL Chat Agent. The system uses Server-Sent Events (SSE) for streaming and a client-side buffer with requestAnimationFrame for smooth token display.

**Last Updated**: December 2, 2025

## Architecture Components

### 1. Backend Streaming (FastAPI + LangGraph)

**Location**: `src/server/server.py`

The backend uses **Server-Sent Events (SSE)** to stream responses in real-time as the LangGraph workflow generates them.

#### Stream Modes

LangGraph supports multiple stream modes that provide different granularities of updates:

- **`values`**: Complete state updates (executed queries, status, summary)
- **`messages`**: Token-by-token streaming from LLM (AIMessageChunk objects)

#### Implementation

```python
for stream_mode, event in graph.stream(
    {
        "user_question": request.message,
        "anticipate_complexity": request.anticipate_complexity,
    },
    config,
    stream_mode=["values", "messages"],  # Both modes enabled
):
    if stream_mode == "values":
        # Full state updates
        event_update = ChatState.model_validate(event)

        # Send status updates
        if event_update.status_update:
            yield f"data: {json.dumps({'type': 'status', 'content': event_update.status_update})}\n\n"

    elif stream_mode == "messages":
        # Token-by-token streaming from LLM
        message_chunk = event[0]
        metadata = event[1] if len(event) > 1 else {}

        # Only stream from generate_query node
        if metadata.get("langgraph_node") == "generate_query":
            if hasattr(message_chunk, "content") and message_chunk.content:
                token = str(message_chunk.content)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
```

#### Event Types

The backend sends multiple event types via SSE:

| Event Type | Description                    | Example Payload                                       |
| ---------- | ------------------------------ | ----------------------------------------------------- |
| `status`   | Processing status updates      | `{"type": "status", "content": "Executing query..."}` |
| `token`    | Individual LLM output tokens   | `{"type": "token", "content": "The"}`                 |
| `message`  | Complete message (fallback)    | `{"type": "message", "content": "Found 156 emails"}`  |
| `queries`  | Executed SQL with explanations | `{"type": "queries", "queries": [...]}`               |
| `summary`  | Overall workflow summary       | `{"type": "summary", "content": "Retrieved counts"}`  |
| `end`      | Stream completion              | `{"type": "end"}`                                     |
| `error`    | Error messages                 | `{"type": "error", "content": "Error message"}`       |

#### Critical Design Choice: Node Filtering

**Only tokens from `generate_query` node are streamed to the frontend.**

This prevents streaming intermediate LLM outputs from other nodes (like `enrich_question` or `generate_explanations`), which would confuse the user experience.

```python
# Extract node name from metadata
node_name = metadata.get("langgraph_node", "")

# Only stream from generate_query node
if node_name == "generate_query":
    # Stream token
    pass
```

### 2. API Client (Frontend)

**Location**: `frontend/lib/api.ts`

The API client handles the SSE connection and parsing of events.

#### SSE Connection

```typescript
const response = await fetch(`${API_BASE_URL}/chat/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message,
    thread_id: threadId,
    anticipate_complexity: anticipateComplexity,
  }),
});

// Read stream using ReadableStream API
const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  // Decode and parse SSE events
  const chunk = decoder.decode(value, { stream: true });
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.substring(6).trim();
      const event = JSON.parse(data);
      handleStreamEvent(event);
    }
  }
}
```

#### Event Handling

The client provides callbacks for each event type:

```typescript
interface StreamCallbacks {
  onToken: (token: string) => void; // Individual token received
  onMessage: (message: string) => void; // Complete message (fallback)
  onQueries: (queries: QueryExecution[]) => void; // SQL queries
  onSummary: (summary: string) => void; // Overall summary
  onStatus: (status: string) => void; // Status updates
  onComplete: () => void; // Stream finished
  onError: (error: string) => void; // Error occurred
}
```

### 3. Client-Side Token Buffering (React Hook)

**Location**: `frontend/hooks/useChatStream.ts`

This is the **core innovation** of the streaming architecture. Instead of updating the UI immediately with each token, tokens are accumulated in a buffer and displayed smoothly using `requestAnimationFrame`.

#### Why Buffering?

**Problem**: Streaming tokens arrive in bursts (network I/O is bursty), causing:

- Jerky, inconsistent rendering
- UI flashing and reflows
- Poor user experience

**Solution**: Client-side buffer with **smooth, time-based token display** at a consistent rate.

#### Buffer Architecture

```typescript
// Token buffer state
const tokenBufferRef = useRef<string>(''); // Accumulated tokens
const displayedLengthRef = useRef<number>(0); // Characters currently displayed
const animationFrameRef = useRef<number | null>(null); // Animation loop ID
const lastUpdateTimeRef = useRef<number>(0); // Last render timestamp

// Streaming parameters
const CHARS_PER_SECOND = 300; // Display rate (configurable)
const MIN_DELAY_MS = 10; // Minimum time between updates
```

#### Smooth Display Loop

The display loop runs continuously during streaming using `requestAnimationFrame`:

```typescript
useEffect(() => {
  const updateDisplay = () => {
    const now = Date.now();
    const deltaTime = now - lastUpdateTimeRef.current;

    // Throttle updates (minimum 10ms between renders)
    if (deltaTime < MIN_DELAY_MS) {
      animationFrameRef.current = requestAnimationFrame(updateDisplay);
      return;
    }

    const buffer = tokenBufferRef.current;
    const displayedLength = displayedLengthRef.current;

    if (displayedLength < buffer.length) {
      // Calculate characters to display based on elapsed time
      const charsToAdd = Math.max(
        1,
        Math.floor((deltaTime / 1000) * CHARS_PER_SECOND)
      );

      const newLength = Math.min(displayedLength + charsToAdd, buffer.length);
      const newText = buffer.substring(0, newLength);

      setCurrentResponse(newText); // Update UI
      displayedLengthRef.current = newLength;
      lastUpdateTimeRef.current = now;
    }

    // Continue loop if streaming or buffer not fully displayed
    if (isStreaming || displayedLength < buffer.length) {
      animationFrameRef.current = requestAnimationFrame(updateDisplay);
    }
  };

  // Start animation loop
  if (
    isStreaming ||
    displayedLengthRef.current < tokenBufferRef.current.length
  ) {
    lastUpdateTimeRef.current = Date.now();
    animationFrameRef.current = requestAnimationFrame(updateDisplay);
  }

  // Cleanup
  return () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  };
}, [isStreaming]);
```

#### Token Accumulation

When tokens arrive from the backend, they are added to the buffer:

```typescript
streamChatMessage(message, threadId, {
  onToken: (token: string) => {
    // Add to buffer (does NOT immediately update UI)
    tokenBufferRef.current += token;
  },

  onMessage: (message: string) => {
    // Fallback for complete messages
    tokenBufferRef.current = message;
  },

  // ... other callbacks
});
```

#### Completion Handling

When the stream ends, ensure all buffered content is displayed:

```typescript
onComplete: () => {
  const finishDisplay = () => {
    if (displayedLengthRef.current < tokenBufferRef.current.length) {
      // Force display of remaining buffer
      setCurrentResponse(tokenBufferRef.current);
      displayedLengthRef.current = tokenBufferRef.current.length;
    }
    setIsStreaming(false);
    cleanupRef.current = null;
  };

  // Small delay for smooth finish
  setTimeout(finishDisplay, 100);
};
```

### 4. UI Components

**Location**: `frontend/components/`

#### ChatMessages Component

**File**: `frontend/components/ChatMessages.tsx`

Displays messages and handles auto-scrolling:

```typescript
useEffect(() => {
  setTimeout(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, 10); // Slight delay for render completion
}, [messages.length]);
```

#### Message Component

**File**: `frontend/components/helpers/Message.tsx`

Renders individual messages with markdown support and query displays:

```typescript
<Message
  role={message.role}
  content={message.content}
  timestamp={message.timestamp}
  queries={message.queries}
  overallSummary={message.overallSummary}
  isStreaming={message.status === 'streaming'}
/>
```

#### StreamingIndicator Component

**File**: `frontend/components/helpers/StreamingIndicator.tsx`

Shows status updates during processing:

```typescript
{
  isStreaming && streamingStatus && (
    <StreamingIndicator status={streamingStatus} />
  );
}
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Backend (Python)                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              LangGraph Workflow                             │ │
│  │                                                             │ │
│  │  enrich_question → generate_query ↔ execute_query         │ │
│  │                         ↓                                   │ │
│  │                 generate_explanations                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           FastAPI /chat/stream endpoint                     │ │
│  │                                                             │ │
│  │  graph.stream(stream_mode=["values", "messages"])          │ │
│  │                                                             │ │
│  │  for stream_mode, event in graph.stream(...):              │ │
│  │    if stream_mode == "messages":                           │ │
│  │      if node == "generate_query":                          │ │
│  │        yield SSE token event                               │ │
│  │    if stream_mode == "values":                             │ │
│  │      yield SSE status/query/summary events                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │ Server-Sent Events (SSE)
                               │ over HTTP connection
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React/Next.js)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              API Client (lib/api.ts)                        │ │
│  │                                                             │ │
│  │  fetch('/chat/stream') → ReadableStream                    │ │
│  │    → TextDecoder → Parse SSE events                        │ │
│  │    → Call callbacks for each event type                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │         useChatStream Hook (hooks/useChatStream.ts)        │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │          Token Buffer Architecture                   │  │ │
│  │  │                                                      │  │ │
│  │  │  onToken(token) {                                    │  │ │
│  │  │    tokenBufferRef.current += token  // Accumulate   │  │ │
│  │  │  }                                                   │  │ │
│  │  │                                                      │  │ │
│  │  │  requestAnimationFrame Loop:                        │  │ │
│  │  │    1. Calculate elapsed time                        │  │ │
│  │  │    2. Compute chars to display (300 chars/sec)      │  │ │
│  │  │    3. Update UI with substring of buffer            │  │ │
│  │  │    4. Continue loop if streaming                    │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │       ChatMessages Component (components/)                  │ │
│  │                                                             │ │
│  │  messages.map(msg => (                                     │ │
│  │    <Message content={currentResponse} />                   │ │
│  │  ))                                                        │ │
│  │                                                             │ │
│  │  Auto-scroll to bottom on update                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               ↓
                         User sees smooth,
                      typewriter-style display
```

## Key Benefits

### 1. Smooth User Experience

- **Consistent rendering**: Tokens display at constant 300 chars/sec regardless of network bursts
- **No UI flashing**: Buffer prevents rapid state changes
- **Typewriter effect**: Natural reading experience

### 2. Performance Optimization

- **Throttling**: Minimum 10ms between renders prevents excessive React updates
- **requestAnimationFrame**: Syncs with browser refresh rate (60 FPS)
- **Efficient string operations**: Substring instead of full re-render

### 3. Network Resilience

- **Buffer absorbs bursts**: Network delays don't affect display smoothness
- **Graceful degradation**: Falls back to complete message if streaming fails
- **Automatic reconnection**: Client handles connection errors transparently

### 4. Developer Experience

- **Separation of concerns**: Network layer, buffering logic, and UI are decoupled
- **Testable**: Each component can be tested independently
- **Configurable**: Adjust `CHARS_PER_SECOND` and `MIN_DELAY_MS` easily

## Configuration Parameters

### Backend

Located in `src/server/server.py`:

```python
# No explicit parameters - LangGraph handles streaming internally
# Node filtering is hardcoded to "generate_query"
```

### Frontend Buffer

Located in `frontend/hooks/useChatStream.ts`:

```typescript
const CHARS_PER_SECOND = 300; // Display rate
const MIN_DELAY_MS = 10; // Throttle interval
```

**Tuning Guidelines**:

- **Fast typing effect**: Increase `CHARS_PER_SECOND` to 500-600
- **Slower, more deliberate**: Decrease to 150-200
- **Performance issues**: Increase `MIN_DELAY_MS` to 16-20 (reduces updates)
- **Smoother animation**: Decrease `MIN_DELAY_MS` to 5 (more updates)

## Error Handling

### Backend Errors

```python
try:
    for stream_mode, event in graph.stream(...):
        # Process events
        pass
except Exception as e:
    error_message = str(e) if str(e) else "An unexpected error occurred"
    error_data = json.dumps({"type": "error", "content": error_message})
    yield f"data: {error_data}\n\n"
```

### Frontend Error Recovery

```typescript
onError: (errorMessage: string) => {
  setError(errorMessage);
  setIsStreaming(false);
  cleanupRef.current = null;
};
```

### Connection Cleanup

```typescript
// Cleanup on unmount or error
useEffect(() => {
  return () => {
    if (cleanupRef.current) {
      cleanupRef.current();
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  };
}, []);
```

## Testing Considerations

### Backend Testing

Test SSE streaming endpoints:

```python
# tests/test_server.py
def test_streaming_endpoint():
    response = client.post("/chat/stream", json={
        "message": "test",
        "thread_id": "test-123",
        "anticipate_complexity": False
    })

    events = []
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            events.append(json.loads(line[6:]))

    assert any(e["type"] == "token" for e in events)
    assert any(e["type"] == "end" for e in events)
```

### Frontend Testing

Test buffer behavior with Jest:

```typescript
// hooks/useChatStream.test.ts
describe('useChatStream buffer', () => {
  it('accumulates tokens in buffer', () => {
    const { result } = renderHook(() => useChatStream());

    act(() => {
      result.current.sendMessage('test', 'thread-1');
    });

    // Simulate tokens arriving
    act(() => {
      onToken('Hello ');
      onToken('World');
    });

    // Buffer should contain both tokens
    expect(tokenBufferRef.current).toBe('Hello World');
  });
});
```

## Future Enhancements

### Potential Improvements

1. **Adaptive Display Rate**: Adjust `CHARS_PER_SECOND` based on token arrival rate
2. **Pause/Resume**: Allow user to pause streaming and resume later
3. **Speed Control**: User-configurable display speed (slider)
4. **Buffer Metrics**: Display buffer size and lag to user
5. **Progressive Enhancement**: Fallback to instant display on slow devices

### Performance Optimizations

1. **Virtual Scrolling**: For very long conversations
2. **Message Pagination**: Lazy load old messages
3. **Web Workers**: Move buffering logic to worker thread
4. **WebSockets**: Replace SSE for bi-directional communication

## Common Issues and Solutions

### Issue: Tokens Not Streaming

**Symptom**: Complete message appears instantly instead of streaming

**Causes**:

1. Backend not sending `token` events
2. Node filtering excluding tokens
3. Network buffering (reverse proxy)

**Solutions**:

```python
# Verify node name in metadata
print(f"Node: {metadata.get('langgraph_node')}")

# Disable nginx buffering
headers = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache"
}
```

### Issue: Jerky Display

**Symptom**: UI updates in large jumps instead of smoothly

**Causes**:

1. `CHARS_PER_SECOND` too high
2. Network bursts overwhelming buffer
3. `MIN_DELAY_MS` too large

**Solutions**:

```typescript
// Reduce display rate
const CHARS_PER_SECOND = 200; // From 300

// Reduce throttle
const MIN_DELAY_MS = 5; // From 10
```

### Issue: Buffer Not Finishing

**Symptom**: Last few characters don't display

**Causes**:

1. Animation loop stops before buffer empty
2. Stream completion too fast
3. Component unmounts early

**Solutions**:

```typescript
// Increase completion delay
setTimeout(finishDisplay, 200); // From 100

// Force immediate display on unmount
useEffect(() => {
  return () => {
    setCurrentResponse(tokenBufferRef.current);
  };
}, []);
```

## Conclusion

The WestBrand streaming architecture provides a **production-ready, smooth streaming experience** through:

1. **Backend**: LangGraph dual-stream mode with node filtering
2. **API Client**: SSE parsing with event-type routing
3. **Buffer**: requestAnimationFrame-based smooth display
4. **UI**: React components with auto-scroll and markdown

This architecture balances **performance, user experience, and maintainability** while remaining **simple and testable**.

---

**Status**: Production Ready  
**Version**: 1.0  
**Last Updated**: December 2, 2025
