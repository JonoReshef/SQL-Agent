/**
 * API Client for WestBrand SQL Chat Agent
 *
 * Provides functions for:
 * - Streaming chat (primary)
 * - Non-streaming chat (fallback)
 * - Conversation history retrieval
 */

import type { components } from '@/types/server/server-types';
import type { QueryExecution, StreamEvent, ApiError } from '@/types/interfaces';

// Type aliases from server schema
type ChatRequest = components['schemas']['ChatRequest'];
type ChatResponse = components['schemas']['ChatResponse'];
type HistoryResponse = components['schemas']['HistoryResponse'];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// Non-Streaming Chat (Fallback)
// ============================================================================

export async function sendChatMessage(
  message: string,
  threadId: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      thread_id: threadId,
    } as ChatRequest),
  });

  if (!response.ok) {
    const error: ApiError = {
      message: `API request failed: ${response.statusText}`,
      statusCode: response.status,
    };
    throw error;
  }

  return response.json();
}

// ============================================================================
// Streaming Chat (Primary) - Server-Sent Events
// ============================================================================

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onMessage: (message: string) => void;
  onQueries: (queries: QueryExecution[]) => void;
  onComplete: () => void;
  onError: (error: string) => void;
}

export function streamChatMessage(
  message: string,
  threadId: string,
  callbacks: StreamCallbacks
): () => void {
  const { onToken, onMessage, onQueries, onComplete, onError } = callbacks;

  let eventSource: EventSource | null = null;
  let isComplete = false;

  // Start streaming request
  const startStream = async () => {
    try {
      // First, make POST request to initiate stream
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          thread_id: threadId,
        } as ChatRequest),
      });

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.statusText}`);
      }

      // Read stream using ReadableStream API
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Response body is not readable');
      }

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          if (!isComplete) {
            onComplete();
            isComplete = true;
          }
          break;
        }

        // Decode chunk and parse SSE events
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.substring(6).trim();
            if (data) {
              try {
                const event: StreamEvent = JSON.parse(data);
                handleStreamEvent(event);
              } catch (parseError) {
                console.error('Failed to parse SSE event:', parseError);
              }
            }
          }
        }
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      onError(errorMessage);
    }
  };

  // Handle individual stream events
  function handleStreamEvent(event: StreamEvent) {
    switch (event.type) {
      case 'token':
        if (event.content) {
          onToken(event.content);
        }
        break;

      case 'message':
        if (event.content) {
          onMessage(event.content);
        }
        break;

      case 'queries':
        if (event.queries) {
          onQueries(event.queries);
        }
        break;

      case 'end':
        if (!isComplete) {
          onComplete();
          isComplete = true;
        }
        break;

      case 'error':
        onError(event.content || 'Unknown error occurred');
        break;

      default:
        console.warn('Unknown event type:', event);
    }
  }

  // Start the stream
  startStream();

  // Return cleanup function
  return () => {
    if (eventSource) {
      eventSource.close();
    }
    isComplete = true;
  };
}

// ============================================================================
// Conversation History
// ============================================================================

export async function getChatHistory(
  threadId: string
): Promise<HistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/history/${threadId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error: ApiError = {
      message: `Failed to fetch history: ${response.statusText}`,
      statusCode: response.status,
    };
    throw error;
  }

  return response.json();
}

// ============================================================================
// Health Check
// ============================================================================

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
