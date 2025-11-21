'use client';

import { useState, useCallback, useRef } from 'react';
import { streamChatMessage } from '@/lib/api';
import type { QueryExecution } from '@/types/interfaces';

export interface UseChatStreamReturn {
  sendMessage: (
    message: string,
    threadId: string,
    anticipateComplexity?: boolean
  ) => Promise<void>;
  isStreaming: boolean;
  currentResponse: string;
  queries: QueryExecution[];
  error: string | null;
  clearError: () => void;
}

/**
 * Custom hook for handling streaming chat with SSE
 */
export function useChatStream(): UseChatStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [queries, setQueries] = useState<QueryExecution[]>([]);
  const [error, setError] = useState<string | null>(null);

  const cleanupRef = useRef<(() => void) | null>(null);

  const sendMessage = useCallback(
    async (
      message: string,
      threadId: string,
      anticipateComplexity: boolean = false
    ) => {
      // Clean up any existing stream
      if (cleanupRef.current) {
        cleanupRef.current();
      }

      // Reset state
      setIsStreaming(true);
      setCurrentResponse('');
      setQueries([]);
      setError(null);

      // Start streaming
      cleanupRef.current = streamChatMessage(
        message,
        threadId,
        {
          onToken: (token: string) => {
            setCurrentResponse((prev) => prev + token);
          },

          onMessage: (message: string) => {
            setCurrentResponse(message);
          },

          onQueries: (newQueries: QueryExecution[]) => {
            setQueries(newQueries);
          },

          onComplete: () => {
            setIsStreaming(false);
            cleanupRef.current = null;
          },

          onError: (errorMessage: string) => {
            setError(errorMessage);
            setIsStreaming(false);
            cleanupRef.current = null;
          },
        },
        anticipateComplexity
      );
    },
    []
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Cleanup on unmount
  useCallback(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, []);

  return {
    sendMessage,
    isStreaming,
    currentResponse,
    queries,
    error,
    clearError,
  };
}
