# Token Streaming Visual Architecture

## High-Level Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                          USER PERSPECTIVE                              │
│                                                                        │
│  Types: "How many emails are in the system?"                         │
│           ↓                                                           │
│  Sees: "Th" → "There" → "There are" → "There are 156"               │
│        (Smooth typewriter effect at 300 chars/sec)                    │
└───────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Flow

### Phase 1: Backend Token Generation

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI Server)                      │
│                                                                  │
│  POST /chat/stream                                              │
│    ↓                                                            │
│  LangGraph.stream(stream_mode=["values", "messages"])          │
│    ↓                                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node: enrich_question                                    │  │
│  │  ├─ LLM expands question                                  │  │
│  │  └─ Emits: status event ("Enriching question...")         │  │
│  └──────────────────────────────────────────────────────────┘  │
│    ↓                                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node: generate_query                                     │  │
│  │  ├─ LLM generates SQL + answer                            │  │
│  │  ├─ Emits: token events ("T", "h", "ere", " are", ...)   │  │
│  │  └─ Filter: Only stream from THIS node                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│    ↓                                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node: execute_query                                      │  │
│  │  ├─ Runs SQL                                              │  │
│  │  └─ Emits: status event ("Executing query...")           │  │
│  └──────────────────────────────────────────────────────────┘  │
│    ↓                                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node: generate_explanations                              │  │
│  │  ├─ Creates SQL explanations                              │  │
│  │  └─ Emits: queries + summary events                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│    ↓                                                            │
│  Server-Sent Events (text/event-stream)                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │ Network (HTTP/SSE)
                           │ data: {"type": "token", "content": "T"}
                           │ data: {"type": "token", "content": "here"}
                           │ data: {"type": "token", "content": " are"}
                           ↓
```

### Phase 2: Frontend Reception & Buffering

```
┌─────────────────────────────────────────────────────────────────┐
│                  Frontend (React/Next.js)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            API Client (lib/api.ts)                        │  │
│  │                                                           │  │
│  │  fetch('/chat/stream')                                    │  │
│  │    ↓                                                      │  │
│  │  response.body.getReader()                                │  │
│  │    ↓                                                      │  │
│  │  TextDecoder → Parse SSE lines                            │  │
│  │    ↓                                                      │  │
│  │  if (line.startsWith("data: "))                          │  │
│  │    event = JSON.parse(line.substring(6))                 │  │
│  │    handleStreamEvent(event)                               │  │
│  │      ↓                                                    │  │
│  │      switch (event.type)                                  │  │
│  │        case "token": → onToken(content)                   │  │
│  │        case "status": → onStatus(content)                 │  │
│  │        case "queries": → onQueries(queries)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      useChatStream Hook (hooks/useChatStream.ts)         │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │         TOKEN BUFFER MECHANISM                       │ │  │
│  │  │                                                      │ │  │
│  │  │  State:                                              │ │  │
│  │  │    tokenBufferRef = ""      // Accumulated tokens   │ │  │
│  │  │    displayedLengthRef = 0   // Characters shown     │ │  │
│  │  │    CHARS_PER_SECOND = 300   // Display rate         │ │  │
│  │  │                                                      │ │  │
│  │  │  onToken(token) {                                    │ │  │
│  │  │    tokenBufferRef.current += token                   │ │  │
│  │  │    // Don't update UI immediately!                   │ │  │
│  │  │  }                                                   │ │  │
│  │  │                                                      │ │  │
│  │  │  Example buffer state:                               │ │  │
│  │  │    t=0ms:   buffer="T"         displayed=""          │ │  │
│  │  │    t=10ms:  buffer="There"     displayed=""          │ │  │
│  │  │    t=20ms:  buffer="There are" displayed="T"         │ │  │
│  │  │    t=30ms:  buffer="There are" displayed="Ther"      │ │  │
│  │  │    t=40ms:  buffer="There are" displayed="There "    │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                           ↓                               │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │     DISPLAY LOOP (requestAnimationFrame)            │ │  │
│  │  │                                                      │ │  │
│  │  │  useEffect(() => {                                   │ │  │
│  │  │    const updateDisplay = () => {                     │ │  │
│  │  │      // 1. Calculate elapsed time                    │ │  │
│  │  │      deltaTime = now - lastUpdateTime                │ │  │
│  │  │                                                      │ │  │
│  │  │      // 2. Throttle (skip if < 10ms)                │ │  │
│  │  │      if (deltaTime < 10ms) return                    │ │  │
│  │  │                                                      │ │  │
│  │  │      // 3. Calculate chars to display                │ │  │
│  │  │      charsToAdd = (deltaTime/1000) * 300            │ │  │
│  │  │                                                      │ │  │
│  │  │      // 4. Update UI with substring                  │ │  │
│  │  │      newText = buffer.substring(0, displayedLen)    │ │  │
│  │  │      setCurrentResponse(newText)                     │ │  │
│  │  │                                                      │ │  │
│  │  │      // 5. Schedule next frame                       │ │  │
│  │  │      requestAnimationFrame(updateDisplay)            │ │  │
│  │  │    }                                                 │ │  │
│  │  │  }, [isStreaming])                                   │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: UI Rendering

```
┌─────────────────────────────────────────────────────────────────┐
│                 React Components (UI Layer)                      │
│                                                                  │
│  ChatInterface                                                   │
│    ↓                                                             │
│  ChatMessages                                                    │
│    ↓                                                             │
│  messages.map(msg => (                                          │
│    <Message                                                      │
│      content={currentResponse}  ← Updated by RAF loop          │
│      isStreaming={true}                                         │
│    />                                                           │
│  ))                                                             │
│                                                                  │
│  Effect: Smooth typewriter display at 300 chars/sec            │
└─────────────────────────────────────────────────────────────────┘
```

## Timing Diagram

```
Time    Backend          Network         Buffer              Display
────────────────────────────────────────────────────────────────────
0ms     LLM: "T"         →               buffer="T"          ""
10ms    LLM: "here"      →               buffer="There"      "T"
20ms    LLM: " are"      →               buffer="There are"  "Th"
30ms                                      buffer="There are"  "Ther"
40ms                                      buffer="There are"  "There"
50ms    LLM: " 156"      →               buffer="...156"     "There "
60ms                                      buffer="...156"     "There a"
...                                       ...                 ...
200ms   end event        →               buffer complete     "There are 156"
```

## Why This Architecture?

### Problem: Direct Streaming (No Buffer)

```
Network Burst Pattern:
Time    Tokens Arrive    UI Updates          User Sees
────────────────────────────────────────────────────────
0ms     "T"              render "T"          "T" (flash)
10ms    "hereare156"     render "There..."   JUMP! (jarring)
100ms   (nothing)        (nothing)           (pause)
110ms   "emails"         render "...emails"  FLASH!
```

Result: Jerky, inconsistent, poor UX

### Solution: Client-Side Buffer

```
Network Burst Pattern:
Time    Tokens Arrive    Buffer              Display
────────────────────────────────────────────────────────
0ms     "T"              "T"                 ""
10ms    "hereare156"     "Thereare156"       "T"
20ms    (nothing)        "Thereare156"       "Th"
30ms    (nothing)        "Thereare156"       "The"
40ms    (nothing)        "Thereare156"       "Ther"
50ms    (nothing)        "Thereare156"       "There"
60ms    (nothing)        "Thereare156"       "There "
```

Result: Smooth, consistent, excellent UX!

## Key Innovations

1. **Dual-Stream Mode**: Backend streams both tokens AND state updates
2. **Node Filtering**: Only tokens from `generate_query` reach frontend
3. **Buffer Accumulation**: Tokens collected without immediate render
4. **requestAnimationFrame**: 60 FPS smooth display loop
5. **Time-Based Display**: Consistent 300 chars/sec regardless of network

## Performance Characteristics

| Metric           | Value         | Notes                               |
| ---------------- | ------------- | ----------------------------------- |
| Display Rate     | 300 chars/sec | Configurable via `CHARS_PER_SECOND` |
| Update Frequency | ~60 FPS       | requestAnimationFrame sync          |
| Throttle         | 10ms minimum  | Prevents excessive renders          |
| Buffer Latency   | 0-100ms       | Depends on network timing           |
| Smoothness       | Perfect       | Independent of network              |

---

**See `STREAMING_ARCHITECTURE.md` for complete technical documentation.**
