# Token Streaming - AI Agent Briefing

## For Another AI Agent Working on This Codebase

This document explains the streaming architecture so you can understand, debug, and extend it.

---

## What Problem Does This Solve?

**Problem**: When streaming LLM responses token-by-token over a network, tokens arrive in **irregular bursts** due to network I/O timing. If you render each token immediately to the UI, users see **jerky, flashing text** that's hard to read.

**Solution**: We accumulate tokens in a client-side buffer and display them at a **consistent, smooth rate** (300 characters/second) using `requestAnimationFrame`. This creates a smooth "typewriter effect" regardless of network timing.

---

## Architecture Overview (3 Layers)

### Layer 1: Backend Token Generation (Python/LangGraph)

**File**: `src/server/server.py`

```python
# LangGraph supports dual-stream mode
for stream_mode, event in graph.stream(
    {...},
    stream_mode=["values", "messages"]  # Both modes!
):
    if stream_mode == "messages":
        # This is token-by-token output from LLM
        message_chunk = event[0]
        metadata = event[1]

        # CRITICAL: Only stream from generate_query node
        if metadata.get("langgraph_node") == "generate_query":
            token = str(message_chunk.content)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    elif stream_mode == "values":
        # This is complete state updates (queries, status, summary)
        yield f"data: {json.dumps({'type': 'status', 'content': status})}\n\n"
```

**Key Points**:

- **Dual-stream mode**: `["values", "messages"]` gives you both complete state AND tokens
- **Node filtering**: Only stream tokens from `generate_query` node (prevents intermediate LLM outputs)
- **Server-Sent Events**: Standard HTTP streaming protocol (`text/event-stream`)

### Layer 2: API Client (TypeScript/React)

**File**: `frontend/lib/api.ts`

```typescript
// Connect to SSE stream
const response = await fetch(`${API_BASE_URL}/chat/stream`, {
  method: 'POST',
  body: JSON.stringify({ message, thread_id, anticipate_complexity }),
});

// Read stream byte by byte
const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  // Parse SSE format: "data: {json}\n\n"
  const chunk = decoder.decode(value, { stream: true });
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.substring(6));

      // Route to appropriate callback
      switch (event.type) {
        case 'token':
          onToken(event.content);
          break;
        case 'status':
          onStatus(event.content);
          break;
        case 'queries':
          onQueries(event.queries);
          break;
        case 'summary':
          onSummary(event.content);
          break;
        case 'end':
          onComplete();
          break;
        case 'error':
          onError(event.content);
          break;
      }
    }
  }
}
```

**Key Points**:

- **ReadableStream API**: Standard browser API for streaming
- **TextDecoder**: Converts bytes to UTF-8 strings
- **Event routing**: Different event types handled by different callbacks

### Layer 3: Client-Side Buffer (React Hook)

**File**: `frontend/hooks/useChatStream.ts`

This is the **core innovation**. Instead of updating UI immediately, we buffer tokens and display them smoothly.

```typescript
// State
const tokenBufferRef = useRef<string>(''); // Accumulated tokens
const displayedLengthRef = useRef<number>(0); // Characters shown
const CHARS_PER_SECOND = 300; // Display rate
const MIN_DELAY_MS = 10; // Update throttle

// When tokens arrive, just accumulate (don't update UI yet!)
const onToken = (token: string) => {
  tokenBufferRef.current += token; // Add to buffer
  // Don't call setCurrentResponse here!
};

// Separate display loop runs continuously
useEffect(() => {
  const updateDisplay = () => {
    const now = Date.now();
    const deltaTime = now - lastUpdateTimeRef.current;

    // Throttle: Skip if too soon
    if (deltaTime < MIN_DELAY_MS) {
      animationFrameRef.current = requestAnimationFrame(updateDisplay);
      return;
    }

    // Calculate how many characters to show based on time
    const charsToAdd = Math.floor((deltaTime / 1000) * CHARS_PER_SECOND);

    // Update UI with substring of buffer
    const newLength = Math.min(
      displayedLengthRef.current + charsToAdd,
      tokenBufferRef.current.length
    );
    const newText = tokenBufferRef.current.substring(0, newLength);
    setCurrentResponse(newText); // NOW update UI

    displayedLengthRef.current = newLength;
    lastUpdateTimeRef.current = now;

    // Continue loop if still streaming or buffer not empty
    if (
      isStreaming ||
      displayedLengthRef.current < tokenBufferRef.current.length
    ) {
      animationFrameRef.current = requestAnimationFrame(updateDisplay);
    }
  };

  // Start loop when streaming begins
  if (isStreaming) {
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

**Key Points**:

- **Separation**: Token arrival (network) is separate from display (UI)
- **requestAnimationFrame**: Browser API syncs with display refresh (60 FPS)
- **Time-based**: Display rate calculated from elapsed time, not token count
- **Throttling**: Minimum 10ms between updates prevents excessive renders

---

## Data Flow Example

Let's trace a single message through the system:

### Step 1: User types "How many emails?"

```
User → ChatInput.tsx → useChatStream.sendMessage() → API Client
```

### Step 2: Backend generates response

```
FastAPI receives request
  ↓
LangGraph workflow starts
  ↓
enrich_question node (status event: "Enriching question...")
  ↓
generate_query node starts
  ↓
LLM generates: "There are 156 emails in the database."
  ↓
Tokens emitted: ["Th", "ere ", "are ", "156", " em", "ails", "..."]
  ↓
SSE events sent:
  data: {"type":"token","content":"Th"}
  data: {"type":"token","content":"ere "}
  data: {"type":"token","content":"are "}
  ...
```

### Step 3: Network transmits (irregular timing)

```
Time    Network Delivers
────────────────────────
0ms     "Th"
5ms     "ere are "      ← Burst! 3 tokens at once
50ms    "156"           ← Gap due to network delay
51ms    " emails..."    ← Another burst
```

### Step 4: Buffer accumulates

```
Time    onToken Called      tokenBufferRef.current
────────────────────────────────────────────────────
0ms     onToken("Th")       "Th"
5ms     onToken("ere ")     "There "
5ms     onToken("are ")     "There are "
50ms    onToken("156")      "There are 156"
51ms    onToken(" em")      "There are 156 em"
...
```

### Step 5: Display loop shows smoothly

```
Time    displayedLengthRef    setCurrentResponse()       User Sees
─────────────────────────────────────────────────────────────────────
0ms     0                     ""                         (empty)
10ms    3                     "The"                      "The"
20ms    6                     "There"                    "There"
30ms    9                     "There ar"                 "There ar"
40ms    12                    "There are 1"              "There are 1"
50ms    15                    "There are 156"            "There are 156"
60ms    18                    "There are 156 em"         "There are 156 em"
...
```

**Notice**: Display updates are **consistent** (every 10ms, 3 characters) regardless of network timing!

---

## Configuration

### Backend (No Config Needed)

The backend automatically handles streaming. You only need to ensure:

1. LangGraph workflow uses `stream_mode=["values", "messages"]`
2. Node filtering is set to `"generate_query"`

### Frontend (Easy to Tune)

**File**: `frontend/hooks/useChatStream.ts` (lines 15-16)

```typescript
const CHARS_PER_SECOND = 300; // Typewriter speed
const MIN_DELAY_MS = 10; // Update frequency
```

**Adjustments**:

- **Faster typing**: Increase `CHARS_PER_SECOND` to 500-600
- **Slower typing**: Decrease to 150-200
- **More frequent updates**: Decrease `MIN_DELAY_MS` to 5
- **Less frequent updates**: Increase to 20

---

## Debugging

### Tokens Not Appearing?

**Check**: Are tokens reaching the buffer?

```typescript
// Add to useChatStream.ts
onToken: (token: string) => {
  console.log('Token received:', token); // Should log each token
  tokenBufferRef.current += token;
};
```

### Display Not Updating?

**Check**: Is the animation loop running?

```typescript
// Add to updateDisplay function
console.log('Display loop:', {
  bufferLength: tokenBufferRef.current.length,
  displayedLength: displayedLengthRef.current,
  isStreaming,
});
```

### Jerky Display?

**Check**: Network bursts overwhelming buffer?

```typescript
// Reduce display rate
const CHARS_PER_SECOND = 200; // From 300

// Or reduce throttle
const MIN_DELAY_MS = 5; // From 10
```

### Backend Not Streaming?

**Check**: Node filtering

```python
# Add to server.py
print(f"Stream mode: {stream_mode}, Node: {metadata.get('langgraph_node')}")
```

If you see nodes other than `"generate_query"`, that's the issue.

---

## Common Modifications

### Change Typing Speed

```typescript
// frontend/hooks/useChatStream.ts
const CHARS_PER_SECOND = 400; // Faster
```

### Add Pause Between Words

```typescript
const updateDisplay = () => {
  // ... existing code ...

  // Check if next character is a space (end of word)
  const nextChar = tokenBufferRef.current[newLength];
  if (nextChar === ' ') {
    // Add small delay between words
    await new Promise((resolve) => setTimeout(resolve, 50));
  }

  // ... rest of code ...
};
```

### Stream from Multiple Nodes

```python
# src/server/server.py
if metadata.get("langgraph_node") in ["generate_query", "generate_explanations"]:
    token = str(message_chunk.content)
    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
```

---

## Testing

### Test Backend Streaming

```bash
# Terminal 1: Start backend
docker-compose up -d

# Terminal 2: Test with curl
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"test","thread_id":"test-123","anticipate_complexity":false}'

# Should see:
# data: {"type":"status","content":"..."}
# data: {"type":"token","content":"T"}
# data: {"type":"token","content":"he"}
# ...
```

### Test Frontend Buffer

```javascript
// frontend/hooks/useChatStream.test.ts
test('buffer accumulates tokens', () => {
  const { result } = renderHook(() => useChatStream());

  act(() => {
    result.current.sendMessage('test', 'thread-1');
  });

  // Simulate tokens
  act(() => {
    onToken('Hello');
    onToken(' World');
  });

  // Buffer should contain both
  expect(tokenBufferRef.current).toBe('Hello World');
});
```

---

## Performance

### Metrics

| Metric           | Value         | Tunable?                |
| ---------------- | ------------- | ----------------------- |
| Display rate     | 300 chars/sec | Yes (CHARS_PER_SECOND)  |
| Update frequency | ~60 FPS       | Yes (MIN_DELAY_MS)      |
| Buffer latency   | 0-100ms       | No (network dependent)  |
| Smoothness       | Perfect       | Yes (tune above params) |

### Optimization Tips

1. **Don't stream too fast**: 300 chars/sec is good for reading
2. **Don't update too often**: 10ms minimum prevents excessive renders
3. **Use requestAnimationFrame**: Syncs with browser refresh
4. **Throttle appropriately**: Balance smoothness vs. performance

---

## Documentation References

- **Complete guide**: `STREAMING_ARCHITECTURE.md` (50+ pages)
- **Quick reference**: `docs/STREAMING_QUICK_REFERENCE.md` (2 pages)
- **Visual guide**: `docs/STREAMING_VISUAL_GUIDE.md` (diagrams)
- **Frontend docs**: `frontend/README.md`

---

## Key Files to Understand

1. `src/server/server.py` - Backend SSE streaming (lines 150-250)
2. `frontend/lib/api.ts` - SSE client and parsing (lines 60-150)
3. `frontend/hooks/useChatStream.ts` - Buffer and RAF loop (entire file)
4. `frontend/components/ChatMessages.tsx` - UI rendering

---

## Summary for AI Agents

**What it does**: Streams LLM responses token-by-token with smooth display

**How it works**:

1. Backend sends tokens via SSE (irregular network timing)
2. Frontend accumulates in buffer (absorbs bursts)
3. Display loop shows consistently at 300 chars/sec (smooth)

**Why it's needed**: Network I/O is bursty; direct rendering is jerky

**Key innovation**: Separation of network layer (irregular) from display layer (smooth)

**Main complexity**: Coordinating async network with sync display loop

**Testing strategy**: Test backend SSE, test frontend buffer, test integration

**Debugging approach**: Check buffer state, check animation loop, check network

**Performance**: Excellent (60 FPS, minimal renders, responsive UI)

---

**Created**: December 2, 2025  
**Status**: Production Ready  
**Maintainability**: High (well-documented, simple architecture)
