'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  fetchThreads,
  createThreadApi,
  updateThreadApi,
  deleteThreadApi,
  deleteAllThreadsApi,
  fetchMessages,
} from '@/lib/api';
import { generateUUID } from '@/lib/utils';
import type {
  Thread,
  ChatMessage,
  ChatMessageModel,
  ThreadResponse,
} from '@/types/interfaces';

const CURRENT_THREAD_KEY = 'westbrand_current';

export interface UseChatThreadsReturn {
  threads: Thread[];
  currentThreadId: string | null;
  currentMessages: ChatMessage[];
  createThread: () => string;
  switchThread: (threadId: string) => Promise<void>;
  deleteThread: (threadId: string) => void;
  clearAllThreads: () => void;
  updateThreadTitle: (threadId: string, title: string) => void;
  addMessage: (threadId: string, message: ChatMessage) => void;
  updateMessageById: (
    threadId: string,
    id: string,
    updates: Partial<ChatMessage>,
  ) => void;
  updateThreadMetadata: (threadId: string, updates: Partial<Thread>) => void;
  isLoading: boolean;
  isInitialised: boolean;
  error: string | null;
}

function apiToThread(t: ThreadResponse): Thread {
  return {
    id: t.id,
    title: t.title,
    lastMessage: t.last_message,
    timestamp: new Date(t.timestamp),
    messageCount: t.message_count,
  };
}

function apiToChatMessage(m: ChatMessageModel): ChatMessage {
  return {
    id: m.id,
    role: m.role as ChatMessage['role'],
    content: m.content,
    timestamp: new Date(m.timestamp),
    status: m.status as ChatMessage['status'],
    queries: m.queries as ChatMessage['queries'],
    overallSummary: m.overall_summary ?? undefined,
  };
}

/**
 * Custom hook for managing chat threads and messages via the backend API.
 *
 * Messages are stored in a thread-indexed map so that operations targeting a
 * specific thread (e.g. adding a streamed message) always land in the correct
 * bucket — even if the user has switched to a different thread in the meantime.
 */
export function useChatThreads(): UseChatThreadsReturn {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messagesByThread, setMessagesByThread] = useState<
    Record<string, ChatMessage[]>
  >({});
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialised, setIsInitialised] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialised = useRef(false);

  // Derive currentMessages from the thread-indexed store
  const currentMessages = useMemo(
    () => (currentThreadId ? (messagesByThread[currentThreadId] ?? []) : []),
    [currentThreadId, messagesByThread],
  );

  // ------------------------------------------------------------------
  // Initialisation: load threads from API
  // ------------------------------------------------------------------
  useEffect(() => {
    if (initialised.current) return;
    initialised.current = true;

    const init = async () => {
      setIsLoading(true);
      try {
        // Load threads from API
        const apiThreads = await fetchThreads();
        const mapped = apiThreads.map(apiToThread);
        setThreads(mapped);

        // Restore current thread selection
        const savedCurrent = localStorage.getItem(CURRENT_THREAD_KEY);
        if (savedCurrent) {
          const parsed = JSON.parse(savedCurrent);
          if (parsed && mapped.some((t) => t.id === parsed)) {
            setCurrentThreadId(parsed);
            const msgs = await fetchMessages(parsed);
            setMessagesByThread({ [parsed]: msgs.map(apiToChatMessage) });
          }
        }
      } catch (err) {
        console.error('Failed to initialise chat threads:', err);
        setError(err instanceof Error ? err.message : 'Failed to load threads');
      } finally {
        setIsLoading(false);
        setIsInitialised(true);
      }
    };

    init();
  }, []);

  // Persist current thread selection locally (lightweight, just the id)
  useEffect(() => {
    if (currentThreadId) {
      localStorage.setItem(CURRENT_THREAD_KEY, JSON.stringify(currentThreadId));
    }
  }, [currentThreadId]);

  // ------------------------------------------------------------------
  // Thread operations
  // ------------------------------------------------------------------

  const createThread = useCallback(() => {
    const newThreadId = generateUUID();
    const newThread: Thread = {
      id: newThreadId,
      title: 'New Chat',
      lastMessage: '',
      timestamp: new Date(),
      messageCount: 0,
    };

    setThreads((prev) => [newThread, ...prev]);
    setCurrentThreadId(newThreadId);
    setMessagesByThread((prev) => ({ ...prev, [newThreadId]: [] }));

    // Fire-and-forget API call
    createThreadApi(newThreadId, 'New Chat').catch((err) =>
      console.error('Failed to persist new thread:', err),
    );

    return newThreadId;
  }, []);

  const switchThread = useCallback(async (threadId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const msgs = await fetchMessages(threadId);
      setMessagesByThread((prev) => ({
        ...prev,
        [threadId]: msgs.map(apiToChatMessage),
      }));
      setCurrentThreadId(threadId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteThread = useCallback(
    (threadId: string) => {
      setThreads((prev) => {
        const remaining = prev.filter((t) => t.id !== threadId);

        if (threadId === currentThreadId) {
          if (remaining.length > 0) {
            setTimeout(() => switchThread(remaining[0].id), 0);
          } else {
            setCurrentThreadId(null);
          }
        }

        return remaining;
      });

      setMessagesByThread((prev) => {
        const next = { ...prev };
        delete next[threadId];
        return next;
      });

      // Fire-and-forget API call
      deleteThreadApi(threadId).catch((err) =>
        console.error('Failed to delete thread from DB:', err),
      );
    },
    [currentThreadId, switchThread],
  );

  const clearAllThreads = useCallback(() => {
    setThreads([]);
    setCurrentThreadId(null);
    setMessagesByThread({});

    deleteAllThreadsApi().catch((err) =>
      console.error('Failed to delete all threads from DB:', err),
    );
  }, []);

  const updateThreadTitle = useCallback((threadId: string, title: string) => {
    setThreads((prev) =>
      prev.map((thread) =>
        thread.id === threadId ? { ...thread, title } : thread,
      ),
    );

    updateThreadApi(threadId, { title }).catch((err) =>
      console.error('Failed to update thread title in DB:', err),
    );
  }, []);

  // ------------------------------------------------------------------
  // Message operations — always target a specific thread by ID
  // ------------------------------------------------------------------

  const addMessage = useCallback((threadId: string, message: ChatMessage) => {
    setMessagesByThread((prev) => ({
      ...prev,
      [threadId]: [...(prev[threadId] ?? []), message],
    }));
  }, []);

  const updateMessageById = useCallback(
    (threadId: string, id: string, updates: Partial<ChatMessage>) => {
      setMessagesByThread((prev) => {
        const messages = prev[threadId];
        if (!messages) return prev;
        return {
          ...prev,
          [threadId]: messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg,
          ),
        };
      });
    },
    [],
  );

  const updateThreadMetadata = useCallback(
    (threadId: string, updates: Partial<Thread>) => {
      setThreads((prev) =>
        prev.map((thread) =>
          thread.id === threadId ? { ...thread, ...updates } : thread,
        ),
      );
    },
    [],
  );

  return {
    threads,
    currentThreadId,
    currentMessages,
    createThread,
    switchThread,
    deleteThread,
    clearAllThreads,
    updateThreadTitle,
    addMessage,
    updateMessageById,
    updateThreadMetadata,
    isLoading,
    isInitialised,
    error,
  };
}
