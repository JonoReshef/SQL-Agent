# WestBrand Chat UI

A modern, responsive chat interface for the WestBrand SQL Chat Agent built with Next.js, React, and TypeScript.

## Features

- ✅ Real-time streaming responses using Server-Sent Events (SSE)
- ✅ Multiple chat thread management
- ✅ SQL query transparency with syntax highlighting
- ✅ Local storage persistence
- ✅ Responsive design (mobile & desktop)
- ✅ Fully typed with TypeScript
- ✅ Auto-generated types from OpenAPI schema

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Backend server running at `http://localhost:8000` (or configured URL)

### Installation

```bash
# Install dependencies
npm install
# or
bun install
```

### Configuration

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
# Start development server
npm run dev
# or
bun dev

# Sync types from backend API
npm run sync-types
```

The application will be available at [http://localhost:3000](http://localhost:3000)

### Building for Production

```bash
npm run build
npm run start
```

## Project Structure

```
frontend/
├── app/                    # Next.js app router
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home (redirects to /chat)
│   ├── globals.css        # Global styles
│   └── chat/
│       └── page.tsx       # Chat page
├── components/            # React components
│   ├── ChatInterface.tsx  # Main container
│   ├── ChatSidebar.tsx    # Thread management
│   ├── ChatMessages.tsx   # Message display
│   ├── ChatInput.tsx      # Input field
│   └── helpers/           # Helper components
│       ├── Message.tsx
│       ├── QueryDisplay.tsx
│       ├── StreamingIndicator.tsx
│       └── ThreadItem.tsx
├── hooks/                 # Custom React hooks
│   ├── useChatStream.ts   # Streaming logic
│   ├── useChatThreads.ts  # Thread management
│   └── useLocalStorage.ts # localStorage wrapper
├── lib/                   # Utilities
│   ├── api.ts            # API client
│   └── utils.ts          # Helper functions
├── types/                 # TypeScript types
│   ├── interfaces.ts     # Shared interfaces
│   └── server/
│       └── server-types.ts # Auto-generated from API
└── scripts/
    └── generate-types.cjs # Type generation script
```

## Key Features

### 1. Streaming Chat

The application uses Server-Sent Events (SSE) to stream responses in real-time from the backend. The `useChatStream` hook handles:

- Token-by-token streaming
- Query result transparency
- Error handling
- Connection management

### 2. Thread Management

Users can:

- Create multiple chat threads
- Switch between conversations
- Delete threads with confirmation
- Auto-save conversations to localStorage

### 3. SQL Query Transparency

All executed SQL queries are displayed with:

- Human-readable explanations
- Syntax-highlighted SQL code
- Result summaries
- Copy-to-clipboard functionality

### 4. Responsive Design

- Mobile-first approach
- Collapsible sidebar on mobile
- Touch-friendly interactions
- Responsive breakpoints

## API Integration

The frontend communicates with the backend via three main endpoints:

1. **POST /chat/stream** - Streaming chat with SSE
2. **POST /chat** - Non-streaming fallback
3. **GET /history/{thread_id}** - Conversation history

## Type Safety

All types are automatically generated from the backend OpenAPI schema:

```bash
npm run sync-types
```

This ensures frontend and backend types stay in sync.

## Development Workflow

1. Start backend server: `python -m src.server.server`
2. Generate types: `npm run sync-types`
3. Start frontend: `npm run dev`
4. Make changes and test
5. Build for production: `npm run build`

## Architecture Decisions

### Functional Components Only

All components use functional React patterns with hooks - no class components.

### Local Storage for Persistence

Conversations are stored locally in the browser for quick access. Future versions may add server-side storage.

### Streaming First

The application prioritizes streaming responses for better UX, with non-streaming as a fallback.

### Component Separation

Helper components are organized in `helpers/` directories alongside their parent components for better maintainability.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

Part of the WestBrand project.
