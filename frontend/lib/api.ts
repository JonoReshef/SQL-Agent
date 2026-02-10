/**
 * API Client for WestBrand SQL Chat Agent
 *
 * Provides functions for:
 * - Streaming chat (primary)
 * - Non-streaming chat (fallback)
 * - Conversation history retrieval
 */

import type {
  ChatRequest,
  ChatResponse,
  HistoryResponse,
  QueryExecution,
  StreamEvent,
  ApiError,
} from '@/types/interfaces';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// Non-Streaming Chat (Fallback)
// ============================================================================

export async function sendChatMessage(
  message: string,
  threadId: string,
  anticipateComplexity: boolean = false
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      thread_id: threadId,
      anticipate_complexity: anticipateComplexity,
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
  onSummary: (summary: string) => void;
  onStatus: (status: string) => void;
  onComplete: () => void;
  onError: (error: string) => void;
}

export function streamChatMessage(
  message: string,
  threadId: string,
  callbacks: StreamCallbacks,
  anticipateComplexity: boolean = false
): () => void {
  const {
    onToken,
    onMessage,
    onQueries,
    onSummary,
    onStatus,
    onComplete,
    onError,
  } = callbacks;

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
          anticipate_complexity: anticipateComplexity,
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
                console.error('Raw data:', data);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      console.error('Error message:', errorMessage);
      onError(errorMessage);
    }
  };

  // Handle individual stream events
  function handleStreamEvent(event: StreamEvent) {
    console.log('Received stream event:', event);
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

      case 'summary':
        if (event.content) {
          onSummary(event.content);
        }
        break;

      case 'status':
        if (event.content) {
          onStatus(event.content);
        }
        break;

      case 'end':
        if (!isComplete) {
          onComplete();
          isComplete = true;
        }
        break;

      case 'error':
        console.error('Stream error event:', event);
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
// Thread CRUD
// ============================================================================

export interface ThreadData {
  id: string;
  title: string;
  last_message: string;
  timestamp: string;
  message_count: number;
}

export interface MessageData {
  id: string;
  role: string;
  content: string;
  timestamp: string;
  status?: string | null;
  queries?: QueryExecution[] | null;
  overall_summary?: string | null;
}

export async function fetchThreads(): Promise<ThreadData[]> {
  const response = await fetch(`${API_BASE_URL}/threads`);
  if (!response.ok) throw new Error(`Failed to fetch threads: ${response.statusText}`);
  const data = await response.json();
  return data.threads;
}

export async function createThreadApi(id: string, title: string = 'New Chat'): Promise<ThreadData> {
  const response = await fetch(`${API_BASE_URL}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, title }),
  });
  if (!response.ok) throw new Error(`Failed to create thread: ${response.statusText}`);
  return response.json();
}

export async function updateThreadApi(
  threadId: string,
  updates: { title?: string; last_message?: string; message_count?: number }
): Promise<ThreadData> {
  const response = await fetch(`${API_BASE_URL}/threads/${threadId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error(`Failed to update thread: ${response.statusText}`);
  return response.json();
}

export async function deleteThreadApi(threadId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/threads/${threadId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Failed to delete thread: ${response.statusText}`);
}

export async function deleteAllThreadsApi(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/threads`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Failed to delete all threads: ${response.statusText}`);
}

// ============================================================================
// Message CRUD
// ============================================================================

export async function fetchMessages(threadId: string): Promise<MessageData[]> {
  const response = await fetch(`${API_BASE_URL}/threads/${threadId}/messages`);
  if (!response.ok) throw new Error(`Failed to fetch messages: ${response.statusText}`);
  return response.json();
}

export async function saveMessageApi(threadId: string, message: MessageData): Promise<MessageData> {
  const response = await fetch(`${API_BASE_URL}/threads/${threadId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  });
  if (!response.ok) throw new Error(`Failed to save message: ${response.statusText}`);
  return response.json();
}

export async function updateMessageApi(
  threadId: string,
  messageId: string,
  updates: { content?: string; status?: string; queries?: QueryExecution[]; overall_summary?: string }
): Promise<MessageData> {
  const response = await fetch(`${API_BASE_URL}/threads/${threadId}/messages/${messageId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error(`Failed to update message: ${response.statusText}`);
  return response.json();
}

// ============================================================================
// Bulk Import (localStorage migration)
// ============================================================================

export async function bulkImportApi(
  threads: { id: string; title: string }[],
  messages: Record<string, MessageData[]>
): Promise<{ imported_threads: number; imported_messages: number }> {
  const response = await fetch(`${API_BASE_URL}/threads/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ threads, messages }),
  });
  if (!response.ok) throw new Error(`Failed to import data: ${response.statusText}`);
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
