'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  fetchThreads,
  createThreadApi,
  updateThreadApi,
  deleteThreadApi,
  deleteAllThreadsApi,
  fetchMessages,
  saveMessageApi,
  updateMessageApi,
  bulkImportApi,
} from '@/lib/api';
import type { MessageData } from '@/lib/api';
import { generateUUID, extractTitle } from '@/lib/utils';
import type { Thread, ChatMessage } from '@/types/interfaces';

// localStorage keys used by the old implementation (for migration)
const THREADS_KEY = 'westbrand_threads';
const CURRENT_THREAD_KEY = 'westbrand_current';
const MESSAGES_KEY_PREFIX = 'westbrand_messages_';
const MIGRATION_DONE_KEY = 'westbrand_migration_done';

export interface UseChatThreadsReturn {
  threads: Thread[];
  currentThreadId: string | null;
  currentMessages: ChatMessage[];
  createThread: () => string;
  switchThread: (threadId: string) => Promise<void>;
  deleteThread: (threadId: string) => void;
  clearAllThreads: () => void;
  updateThreadTitle: (threadId: string, title: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessageById: (id: string, updates: Partial<ChatMessage>) => void;
  isLoading: boolean;
  isInitialised: boolean;
  error: string | null;
}

function chatMessageToApi(msg: ChatMessage): MessageData {
  return {
    id: msg.id,
    role: msg.role,
    content: msg.content,
    timestamp:
      msg.timestamp instanceof Date
        ? msg.timestamp.toISOString()
        : msg.timestamp,
    status: msg.status ?? null,
    queries: msg.queries ?? null,
    overall_summary: msg.overallSummary ?? null,
  };
}

function apiToThread(t: { id: string; title: string; last_message: string; timestamp: string; message_count: number }): Thread {
  return {
    id: t.id,
    title: t.title,
    lastMessage: t.last_message,
    timestamp: new Date(t.timestamp),
    messageCount: t.message_count,
  };
}

function apiToChatMessage(m: MessageData): ChatMessage {
  return {
    id: m.id,
    role: m.role as ChatMessage['role'],
    content: m.content,
    timestamp: new Date(m.timestamp),
    status: m.status as ChatMessage['status'],
    queries: m.queries ?? undefined,
    overallSummary: m.overall_summary ?? undefined,
  };
}

/**
 * Custom hook for managing chat threads and messages via the backend API.
 * On first load, migrates any existing localStorage data to the database.
 */
export function useChatThreads(): UseChatThreadsReturn {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialised, setIsInitialised] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialised = useRef(false);

  // ------------------------------------------------------------------
  // Initialisation: migrate localStorage then load threads from API
  // ------------------------------------------------------------------
  useEffect(() => {
    if (initialised.current) return;
    initialised.current = true;

    const init = async () => {
      setIsLoading(true);
      try {
        // Migrate localStorage data if not already done
        await migrateLocalStorage();

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
            setCurrentMessages(msgs.map(apiToChatMessage));
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
  // localStorage → API migration (runs once)
  // ------------------------------------------------------------------
  async function migrateLocalStorage() {
    if (typeof window === 'undefined') return;
    if (localStorage.getItem(MIGRATION_DONE_KEY)) return;

    const storedThreads = localStorage.getItem(THREADS_KEY);
    if (!storedThreads) {
      localStorage.setItem(MIGRATION_DONE_KEY, '1');
      return;
    }

    try {
      const parsedThreads: Thread[] = JSON.parse(storedThreads);
      if (!parsedThreads.length) {
        localStorage.setItem(MIGRATION_DONE_KEY, '1');
        return;
      }

      const threadPayloads = parsedThreads.map((t) => ({
        id: t.id,
        title: t.title,
      }));

      const messagesPayload: Record<string, MessageData[]> = {};
      for (const t of parsedThreads) {
        const raw = localStorage.getItem(`${MESSAGES_KEY_PREFIX}${t.id}`);
        if (raw) {
          try {
            const msgs: ChatMessage[] = JSON.parse(raw);
            messagesPayload[t.id] = msgs.map(chatMessageToApi);
          } catch {
            // skip malformed message data
          }
        }
      }

      await bulkImportApi(threadPayloads, messagesPayload);

      // Clean up old localStorage keys
      localStorage.removeItem(THREADS_KEY);
      for (const t of parsedThreads) {
        localStorage.removeItem(`${MESSAGES_KEY_PREFIX}${t.id}`);
      }
      localStorage.setItem(MIGRATION_DONE_KEY, '1');
      console.log('Successfully migrated localStorage data to database');
    } catch (err) {
      console.error('Migration failed, will retry next load:', err);
      // Don't mark as done so it retries
    }
  }

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
    setCurrentMessages([]);

    // Fire-and-forget API call
    createThreadApi(newThreadId, 'New Chat').catch((err) =>
      console.error('Failed to persist new thread:', err)
    );

    return newThreadId;
  }, []);

  const switchThread = useCallback(async (threadId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const msgs = await fetchMessages(threadId);
      setCurrentMessages(msgs.map(apiToChatMessage));
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
            setCurrentMessages([]);
          }
        }

        return remaining;
      });

      // Fire-and-forget API call
      deleteThreadApi(threadId).catch((err) =>
        console.error('Failed to delete thread from DB:', err)
      );
    },
    [currentThreadId, switchThread]
  );

  const clearAllThreads = useCallback(() => {
    setThreads([]);
    setCurrentThreadId(null);
    setCurrentMessages([]);

    deleteAllThreadsApi().catch((err) =>
      console.error('Failed to delete all threads from DB:', err)
    );
  }, []);

  const updateThreadTitle = useCallback((threadId: string, title: string) => {
    setThreads((prev) =>
      prev.map((thread) =>
        thread.id === threadId ? { ...thread, title } : thread
      )
    );

    updateThreadApi(threadId, { title }).catch((err) =>
      console.error('Failed to update thread title in DB:', err)
    );
  }, []);

  // ------------------------------------------------------------------
  // Message operations
  // ------------------------------------------------------------------

  const addMessage = useCallback(
    (message: ChatMessage) => {
      if (!currentThreadId) return;

      setCurrentMessages((prev) => [...prev, message]);

      // Update thread metadata in local state
      setThreads((prevThreads) =>
        prevThreads.map((thread) => {
          if (thread.id === currentThreadId) {
            const newTitle =
              thread.title === 'New Chat' && message.role === 'user'
                ? extractTitle(message.content)
                : thread.title;

            return {
              ...thread,
              title: newTitle,
              lastMessage: message.content,
              timestamp: message.timestamp,
              messageCount: thread.messageCount + 1,
            };
          }
          return thread;
        })
      );

      // Persist to API
      const threadId = currentThreadId;
      saveMessageApi(threadId, chatMessageToApi(message)).catch((err) =>
        console.error('Failed to save message to DB:', err)
      );

      // Update thread title if it changed
      const thread = threads.find((t) => t.id === currentThreadId);
      if (thread?.title === 'New Chat' && message.role === 'user') {
        const newTitle = extractTitle(message.content);
        updateThreadApi(threadId, { title: newTitle }).catch((err) =>
          console.error('Failed to update thread title in DB:', err)
        );
      }
    },
    [currentThreadId, threads]
  );

  const updateMessageById = useCallback(
    (id: string, updates: Partial<ChatMessage>) => {
      if (!currentThreadId) return;

      setCurrentMessages((prev) =>
        prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
      );

      // Update thread metadata if content changed
      if (updates.content) {
        setThreads((prevThreads) =>
          prevThreads.map((thread) =>
            thread.id === currentThreadId
              ? {
                  ...thread,
                  lastMessage: updates.content!,
                  timestamp: updates.timestamp ?? thread.timestamp,
                }
              : thread
          )
        );
      }

      // Persist to API
      const apiUpdates: Record<string, unknown> = {};
      if (updates.content !== undefined) apiUpdates.content = updates.content;
      if (updates.status !== undefined) apiUpdates.status = updates.status;
      if (updates.queries !== undefined) apiUpdates.queries = updates.queries;
      if (updates.overallSummary !== undefined) apiUpdates.overall_summary = updates.overallSummary;

      if (Object.keys(apiUpdates).length > 0) {
        updateMessageApi(currentThreadId, id, apiUpdates as any).catch((err) =>
          console.error('Failed to update message in DB:', err)
        );
      }
    },
    [currentThreadId]
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
    isLoading,
    isInitialised,
    error,
  };
}
