# WestBrand Streaming Documentation - Index

## Documentation Overview

This directory contains comprehensive documentation for the WestBrand SQL Chat Agent's streaming architecture. The system implements real-time token-by-token streaming with client-side buffering for smooth, responsive user experience.

## Document Guide

### For Quick Understanding

**Start here**: `STREAMING_QUICK_REFERENCE.md`

- 2-page overview of the architecture
- Key code snippets
- Common issues and solutions
- Best for: Developers new to the codebase

**Visual Guide**: `STREAMING_VISUAL_GUIDE.md`

- ASCII diagrams showing data flow
- Timing diagrams
- Component relationships
- Best for: Visual learners, architecture reviews

**AI Agent Briefing**: `STREAMING_AI_BRIEFING.md` (NEW)

- Comprehensive guide designed for AI agents
- Problem/solution explanation
- Step-by-step walkthrough with examples
- Debugging and modification guides
- Best for: AI assistants, onboarding, troubleshooting

### For Deep Technical Details

**Complete Guide**: `../STREAMING_ARCHITECTURE.md` (root directory)

- 50+ page comprehensive documentation
- Complete code examples
- Testing strategies
- Performance tuning
- Error handling patterns
- Best for: Implementation, debugging, optimization

### For Implementation

**Frontend**: `../frontend/README.md`

- Next.js setup and configuration
- Component structure
- Custom hooks (useChatStream, useChatThreads)
- Development workflow

**Backend**: `../src/server/server.py`

- FastAPI implementation
- LangGraph integration
- SSE streaming setup
- Event type handling

**Chat Workflow**: `../src/chat_workflow/README.md`

- LangGraph workflow nodes
- SQL generation logic
- Conversation persistence

## Key Concepts

### 1. Dual-Stream Mode

Backend uses LangGraph's dual-stream capability:

- `values`: Complete state updates (queries, status, summary)
- `messages`: Token-by-token LLM output

### 2. Client-Side Buffer

Frontend accumulates tokens in a buffer and displays them smoothly:

- Tokens arrive in network bursts (irregular)
- Buffer absorbs timing variations
- Display loop shows consistent 300 chars/sec (smooth)

### 3. requestAnimationFrame Loop

Browser-synced display loop (60 FPS):

- Calculates characters to display based on elapsed time
- Updates UI substring of buffer
- Continues until buffer fully displayed

## Architecture at a Glance

```
Backend:     LangGraph → SSE Token Stream → Network
                            ↓
Frontend:    Buffer Accumulation → RAF Display Loop → Smooth UI
                (bursts)              (300 chars/sec)    (typewriter)
```

## File Locations

### Core Implementation

- `frontend/hooks/useChatStream.ts` - Buffer + RAF loop
- `frontend/lib/api.ts` - SSE connection + parsing
- `src/server/server.py` - FastAPI streaming endpoint
- `src/chat_workflow/graph.py` - LangGraph workflow

### Configuration

- `frontend/hooks/useChatStream.ts:15-16` - Display rate constants
  - `CHARS_PER_SECOND = 300`
  - `MIN_DELAY_MS = 10`

### Documentation

- `STREAMING_ARCHITECTURE.md` - Complete technical guide
- `docs/STREAMING_QUICK_REFERENCE.md` - Quick reference
- `docs/STREAMING_VISUAL_GUIDE.md` - Visual diagrams
- `frontend/README.md` - Frontend setup

## Quick Links

### Common Tasks

**Adjust typing speed**:

```typescript
// frontend/hooks/useChatStream.ts
const CHARS_PER_SECOND = 300; // Change this value
```

**Change update frequency**:

```typescript
// frontend/hooks/useChatStream.ts
const MIN_DELAY_MS = 10; // Lower = more frequent updates
```

**Debug buffer state**:

```typescript
// Add to useChatStream hook
console.log('Buffer:', tokenBufferRef.current);
console.log('Displayed:', displayedLengthRef.current);
```

**Test streaming**:

```bash
# Start backend
docker-compose up -d

# Open frontend
open http://localhost:3000

# Send test message
```

## Reading Order Recommendations

### For New Developers

1. `STREAMING_AI_BRIEFING.md` (30 min) - Comprehensive onboarding
2. `STREAMING_QUICK_REFERENCE.md` (10 min) - Quick overview
3. `STREAMING_VISUAL_GUIDE.md` (15 min) - Visual understanding
4. Review code: `frontend/hooks/useChatStream.ts` (20 min)
5. Deep dive: `STREAMING_ARCHITECTURE.md` (as needed)

### For Code Review

1. `STREAMING_VISUAL_GUIDE.md` - Understand architecture
2. Review implementation files directly
3. Reference `STREAMING_ARCHITECTURE.md` for specific patterns

### For Debugging

1. `STREAMING_QUICK_REFERENCE.md` - Common issues section
2. `STREAMING_ARCHITECTURE.md` - Complete error handling
3. Check specific code files based on issue

### For Optimization

1. `STREAMING_ARCHITECTURE.md` - Performance section
2. `STREAMING_QUICK_REFERENCE.md` - Configuration parameters
3. Profile and test with actual usage patterns

## Version History

- **v1.0** (December 2, 2025) - Initial streaming documentation
  - Token-by-token streaming with LangGraph
  - Client-side buffering with requestAnimationFrame
  - Complete technical documentation

## Related Documentation

- `../README.md` - Project overview and setup
- `../.github/copilot-instructions.md` - AI agent instructions
- `../frontend/README.md` - Frontend architecture
- `../src/chat_workflow/README.md` - Chat workflow details

## Feedback and Updates

This documentation is maintained alongside the codebase. When streaming architecture changes:

1. Update `STREAMING_ARCHITECTURE.md` first (source of truth)
2. Update quick reference and visual guide as needed
3. Update code comments to match documentation
4. Test all examples to ensure accuracy

---

**Documentation Status**: Complete  
**Last Updated**: December 2, 2025  
**Maintainer**: WestBrand Development Team
