# Streaming Architecture - Quick Reference

## Overview

WestBrand implements real-time streaming chat with **token-by-token display** and **client-side buffering** for smooth user experience.

## Key Components

### 1. Backend (Python/FastAPI)

**File**: `src/server/server.py`

```python
# Dual-stream mode for granular updates
for stream_mode, event in graph.stream(
    {...},
    stream_mode=["values", "messages"]
):
    if stream_mode == "messages":  # Token-by-token
        if metadata.get("langgraph_node") == "generate_query":
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    elif stream_mode == "values":  # Full state updates
        yield f"data: {json.dumps({'type': 'status', 'content': status})}\n\n"
```

### 2. Frontend Buffer (TypeScript/React)

**File**: `frontend/hooks/useChatStream.ts`

```typescript
// Buffer configuration
const CHARS_PER_SECOND = 300; // Display rate
const MIN_DELAY_MS = 10; // Update throttle

// Accumulate tokens
onToken: (token: string) => {
  tokenBufferRef.current += token; // Don't update UI yet
};

// Display loop (requestAnimationFrame)
const updateDisplay = () => {
  const charsToAdd = Math.floor((deltaTime / 1000) * CHARS_PER_SECOND);
  const newText = buffer.substring(0, displayedLength + charsToAdd);
  setCurrentResponse(newText); // Update UI smoothly
};
```

## Data Flow

```
Backend LLM → Token Stream → SSE → API Client → Buffer → RAF Loop → UI
                                                  ↓
                                         300 chars/sec
                                         smooth display
```

## Event Types

| Type      | When          | Purpose               |
| --------- | ------------- | --------------------- |
| `token`   | LLM generates | Individual characters |
| `status`  | Node changes  | "Executing query..."  |
| `message` | Fallback      | Complete response     |
| `queries` | SQL executed  | Transparency          |
| `summary` | Workflow done | Overall result        |
| `end`     | Stream done   | Cleanup signal        |
| `error`   | Exception     | Error message         |

## Key Parameters

### Backend

- **Stream Mode**: `["values", "messages"]` - Both modes enabled
- **Node Filter**: `generate_query` - Only stream from this node

### Frontend

- **Display Rate**: `300` chars/sec - Configurable typewriter speed
- **Throttle**: `10` ms - Minimum time between UI updates
- **Buffer**: `tokenBufferRef` - Accumulates all tokens
- **Display**: `requestAnimationFrame` - 60 FPS smooth rendering

## Common Issues

### Tokens arrive but don't display

- Check `node_name == "generate_query"` filter
- Verify buffer is updating: `console.log(tokenBufferRef.current)`
- Check animation loop is running: `animationFrameRef.current !== null`

### Display is jerky

- Reduce `CHARS_PER_SECOND` (try 200)
- Reduce `MIN_DELAY_MS` (try 5)
- Check network latency causing token bursts

### Last tokens missing

- Increase completion delay: `setTimeout(finishDisplay, 200)`
- Force display on unmount: `setCurrentResponse(tokenBufferRef.current)`

## Architecture Benefits

1. **Smooth UX**: Consistent 300 chars/sec regardless of network
2. **Efficient**: Throttled updates prevent excessive React renders
3. **Resilient**: Buffer absorbs network bursts gracefully
4. **Testable**: Decoupled components easy to test independently

## Complete Documentation

See **`STREAMING_ARCHITECTURE.md`** for comprehensive technical details including:

- Complete code examples
- Error handling strategies
- Testing approaches
- Performance tuning guidelines
- Debugging techniques

## Quick Test

```bash
# Start backend
docker-compose up -d

# Frontend auto-connects to http://localhost:8000
open http://localhost:3000

# Send message and watch smooth streaming
```

---

**Version**: 1.0  
**Last Updated**: December 2, 2025
