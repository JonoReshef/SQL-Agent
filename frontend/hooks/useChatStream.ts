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
  currentStatus: string;
  queries: QueryExecution[];
  overallSummary: string;
  error: string | null;
  clearError: () => void;
}

/**
 * Custom hook for handling streaming chat with SSE
 */
export function useChatStream(): UseChatStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentStatus, setCurrentStatus] = useState('');
  const [queries, setQueries] = useState<QueryExecution[]>([]);
  const [overallSummary, setOverallSummary] = useState('');
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
      setCurrentStatus('');
      setQueries([]);
      setOverallSummary('');
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

          onSummary: (summary: string) => {
            setOverallSummary(summary);
          },

          onStatus: (status: string) => {
            setCurrentStatus(status);
          },

          onComplete: () => {
            setIsStreaming(false);
            setCurrentStatus('');
            cleanupRef.current = null;
          },

          onError: (errorMessage: string) => {
            setError(errorMessage);
            setIsStreaming(false);
            setCurrentStatus('');
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
    currentStatus,
    queries,
    overallSummary,
    error,
    clearError,
  };
}
