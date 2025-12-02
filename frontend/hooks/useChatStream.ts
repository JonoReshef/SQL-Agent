'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
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
 * Custom hook for handling streaming chat with SSE and smooth token buffering
 */
export function useChatStream(): UseChatStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentStatus, setCurrentStatus] = useState('');
  const [queries, setQueries] = useState<QueryExecution[]>([]);
  const [overallSummary, setOverallSummary] = useState('');
  const [error, setError] = useState<string | null>(null);

  const cleanupRef = useRef<(() => void) | null>(null);

  // Token buffering for smooth streaming
  const tokenBufferRef = useRef<string>('');
  const displayedLengthRef = useRef<number>(0);
  const animationFrameRef = useRef<number | null>(null);
  const lastUpdateTimeRef = useRef<number>(0);

  // Smooth streaming parameters
  const CHARS_PER_SECOND = 300; // Characters per second for display
  const MIN_DELAY_MS = 10; // Minimum delay between updates

  // Smooth token display loop
  useEffect(() => {
    const updateDisplay = () => {
      const now = Date.now();
      const deltaTime = now - lastUpdateTimeRef.current;

      if (deltaTime < MIN_DELAY_MS) {
        animationFrameRef.current = requestAnimationFrame(updateDisplay);
        return;
      }

      const buffer = tokenBufferRef.current;
      const displayedLength = displayedLengthRef.current;

      if (displayedLength < buffer.length) {
        // Calculate how many characters to add based on elapsed time
        const charsToAdd = Math.max(
          1,
          Math.floor((deltaTime / 1000) * CHARS_PER_SECOND)
        );

        const newLength = Math.min(displayedLength + charsToAdd, buffer.length);
        const newText = buffer.substring(0, newLength);

        setCurrentResponse(newText);
        displayedLengthRef.current = newLength;
        lastUpdateTimeRef.current = now;
      }

      // Continue animation if streaming or buffer not fully displayed
      if (isStreaming || displayedLength < buffer.length) {
        animationFrameRef.current = requestAnimationFrame(updateDisplay);
      }
    };

    if (
      isStreaming ||
      displayedLengthRef.current < tokenBufferRef.current.length
    ) {
      lastUpdateTimeRef.current = Date.now();
      animationFrameRef.current = requestAnimationFrame(updateDisplay);
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isStreaming]);

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

      // Reset buffer
      tokenBufferRef.current = '';
      displayedLengthRef.current = 0;

      // Start streaming
      cleanupRef.current = streamChatMessage(
        message,
        threadId,
        {
          onToken: (token: string) => {
            // Add to buffer instead of directly updating display
            tokenBufferRef.current += token;
          },

          onMessage: (message: string) => {
            // For fallback complete messages, set buffer directly
            tokenBufferRef.current = message;
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
            // Ensure all buffered content is displayed before marking complete
            const finishDisplay = () => {
              if (displayedLengthRef.current < tokenBufferRef.current.length) {
                setCurrentResponse(tokenBufferRef.current);
                displayedLengthRef.current = tokenBufferRef.current.length;
              }
              setIsStreaming(false);
              setCurrentStatus('');
              cleanupRef.current = null;
            };

            // Small delay to ensure smooth finish
            setTimeout(finishDisplay, 100);
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
  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
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
