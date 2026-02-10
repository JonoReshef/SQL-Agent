/**
 * Shared TypeScript interfaces for WestBrand Chat UI
 *
 * These types are used across multiple components. Where possible, types
 * are exported from server-types.ts (auto-generated from OpenAPI schema).
 * Frontend-specific types that don't exist on the backend remain here.
 */

import type { components } from './server/server-types';

// ============================================================================
// Server Types (Re-exported from OpenAPI schema)
// ============================================================================

/**
 * Query execution details with SQL transparency
 * Maps to server's QueryExecutionResponse
 */
export type QueryExecution = components['schemas']['QueryExecutionResponse'];

/**
 * Chat request payload
 * Maps to server's ChatRequest
 */
export type ChatRequest = components['schemas']['ChatRequest'];

/**
 * Chat response payload
 * Maps to server's ChatResponse
 */
export type ChatResponse = components['schemas']['ChatResponse'];

/**
 * History response payload
 * Maps to server's HistoryResponse
 */
export type HistoryResponse = components['schemas']['HistoryResponse'];

/**
 * Thread response from API
 * Maps to server's ThreadResponse
 */
export type ThreadResponse = components['schemas']['ThreadResponse'];

/**
 * Thread list response from API
 * Maps to server's ThreadListResponse
 */
export type ThreadListResponse = components['schemas']['ThreadListResponse'];

/**
 * Chat message as returned by the API
 * Maps to server's ChatMessageModel
 */
export type ChatMessageModel = components['schemas']['ChatMessageModel'];

/**
 * Request to save a message
 * Maps to server's SaveMessageRequest
 */
export type SaveMessageRequest = components['schemas']['SaveMessageRequest'];

/**
 * Request to update a message
 * Maps to server's UpdateMessageRequest
 */
export type UpdateMessageRequest = components['schemas']['UpdateMessageRequest'];

/**
 * Request to create a thread
 * Maps to server's CreateThreadRequest
 */
export type CreateThreadRequest = components['schemas']['CreateThreadRequest'];

/**
 * Request to update a thread
 * Maps to server's UpdateThreadRequest
 */
export type UpdateThreadRequest = components['schemas']['UpdateThreadRequest'];

/**
 * Request to bulk import threads and messages
 * Maps to server's BulkImportRequest
 */
export type BulkImportRequest = components['schemas']['BulkImportRequest'];

// ============================================================================
// Thread Management (Frontend-only)
// ============================================================================

export interface Thread {
  id: string; // UUID v4
  title: string; // First message or "New Chat"
  lastMessage: string; // Preview text
  timestamp: Date | string; // Date object or ISO string from localStorage
  messageCount: number;
}

// ============================================================================
// Chat Messages (Frontend-only - Local State)
// ============================================================================

export type MessageRole = 'user' | 'assistant' | 'system';
export type MessageStatus = 'streaming' | 'complete';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date | string; // Date object or ISO string from localStorage
  status?: MessageStatus; // Indicates if message is still being streamed
  queries?: QueryExecution[]; // For assistant messages with SQL transparency
  overallSummary?: string; // High-level summary of the entire query process
}

// ============================================================================
// Streaming Events (Frontend-only - SSE)
// ============================================================================

export type StreamEventType =
  | 'token'
  | 'message'
  | 'queries'
  | 'summary'
  | 'status'
  | 'end'
  | 'error';

export interface StreamEvent {
  type: StreamEventType;
  content?: string;
  queries?: QueryExecution[];
}

// ============================================================================
// Utility Types (Frontend-only)
// ============================================================================

export interface ApiError {
  message: string;
  statusCode?: number;
}
