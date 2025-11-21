/**
 * Shared TypeScript interfaces for WestBrand Chat UI
 *
 * These types are used across multiple components and differ from
 * server-types.ts which are auto-generated from the OpenAPI schema.
 */

// ============================================================================
// Thread Management
// ============================================================================

export interface Thread {
  id: string; // UUID v4
  title: string; // First message or "New Chat"
  lastMessage: string; // Preview text
  timestamp: Date;
  messageCount: number;
}

// ============================================================================
// Chat Messages (Local State)
// ============================================================================

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  queries?: QueryExecution[]; // For assistant messages with SQL transparency
}

// ============================================================================
// Query Execution (matches server QueryExecutionResponse)
// ============================================================================

export interface QueryExecution {
  query: string;
  explanation: string;
  resultSummary: string;
}

// ============================================================================
// Streaming Events (SSE)
// ============================================================================

export type StreamEventType = 'token' | 'message' | 'queries' | 'end' | 'error';

export interface StreamEvent {
  type: StreamEventType;
  content?: string;
  queries?: QueryExecution[];
}

// ============================================================================
// Utility Types
// ============================================================================

export interface ApiError {
  message: string;
  statusCode?: number;
}
