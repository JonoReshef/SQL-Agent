'use client';

import { useState, useCallback, useEffect } from 'react';
import { useLocalStorage } from './useLocalStorage';
import { getChatHistory } from '@/lib/api';
import { generateUUID, extractTitle } from '@/lib/utils';
import type { Thread, ChatMessage } from '@/types/interfaces';

const THREADS_KEY = 'westbrand_threads';
const CURRENT_THREAD_KEY = 'westbrand_current';
const MESSAGES_KEY_PREFIX = 'westbrand_messages_';

export interface UseChatThreadsReturn {
  threads: Thread[];
  currentThreadId: string | null;
  currentMessages: ChatMessage[];
  createThread: () => string;
  switchThread: (threadId: string) => Promise<void>;
  deleteThread: (threadId: string) => void;
  updateThreadTitle: (threadId: string, title: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (message: ChatMessage) => void;
  isLoading: boolean;
  error: string | null;
}

/**
 * Custom hook for managing chat threads and messages
 */
export function useChatThreads(): UseChatThreadsReturn {
  const [threads, setThreads] = useLocalStorage<Thread[]>(THREADS_KEY, []);
  const [currentThreadId, setCurrentThreadId] = useLocalStorage<string | null>(
    CURRENT_THREAD_KEY,
    null
  );
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load messages for current thread
  useEffect(() => {
    if (!currentThreadId) {
      setCurrentMessages([]);
      return;
    }

    // Load from localStorage
    const messagesKey = `${MESSAGES_KEY_PREFIX}${currentThreadId}`;
    const stored = localStorage.getItem(messagesKey);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Convert timestamp strings back to Date objects
        const messages = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setCurrentMessages(messages);
      } catch (err) {
        console.error('Error loading messages:', err);
        setCurrentMessages([]);
      }
    } else {
      setCurrentMessages([]);
    }
  }, [currentThreadId]);

  // Save messages to localStorage whenever they change
  const saveMessages = useCallback(
    (threadId: string, messages: ChatMessage[]) => {
      const messagesKey = `${MESSAGES_KEY_PREFIX}${threadId}`;
      localStorage.setItem(messagesKey, JSON.stringify(messages));
    },
    []
  );

  // Create new thread
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

    return newThreadId;
  }, [setThreads, setCurrentThreadId]);

  // Switch to different thread
  const switchThread = useCallback(
    async (threadId: string) => {
      setIsLoading(true);
      setError(null);

      try {
        // Load messages from localStorage
        const messagesKey = `${MESSAGES_KEY_PREFIX}${threadId}`;
        const stored = localStorage.getItem(messagesKey);

        if (stored) {
          const parsed = JSON.parse(stored);
          const messages = parsed.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          }));
          setCurrentMessages(messages);
        } else {
          // Try to load from server history
          try {
            const history = await getChatHistory(threadId);
            // Convert history to ChatMessage format
            const messages: ChatMessage[] = [];
            for (const checkpoint of history.history) {
              if (checkpoint.messages) {
                for (const msg of checkpoint.messages) {
                  messages.push({
                    id: generateUUID(),
                    role: msg.type === 'HumanMessage' ? 'user' : 'assistant',
                    content: msg.content,
                    timestamp: checkpoint.timestamp
                      ? new Date(checkpoint.timestamp)
                      : new Date(),
                  });
                }
              }
            }
            setCurrentMessages(messages);
            saveMessages(threadId, messages);
          } catch (historyError) {
            console.warn('Failed to load history from server:', historyError);
            setCurrentMessages([]);
          }
        }

        setCurrentThreadId(threadId);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [setCurrentThreadId, saveMessages]
  );

  // Delete thread
  const deleteThread = useCallback(
    (threadId: string) => {
      // Remove from threads list
      setThreads((prev) => prev.filter((t) => t.id !== threadId));

      // Remove messages from localStorage
      const messagesKey = `${MESSAGES_KEY_PREFIX}${threadId}`;
      localStorage.removeItem(messagesKey);

      // If deleted current thread, switch to most recent or create new
      if (threadId === currentThreadId) {
        const remainingThreads = threads.filter((t) => t.id !== threadId);
        if (remainingThreads.length > 0) {
          switchThread(remainingThreads[0].id);
        } else {
          createThread();
        }
      }
    },
    [threads, currentThreadId, setThreads, switchThread, createThread]
  );

  // Update thread title
  const updateThreadTitle = useCallback(
    (threadId: string, title: string) => {
      setThreads((prev) =>
        prev.map((thread) =>
          thread.id === threadId ? { ...thread, title } : thread
        )
      );
    },
    [setThreads]
  );

  // Add new message to current thread
  const addMessage = useCallback(
    (message: ChatMessage) => {
      if (!currentThreadId) return;

      const updatedMessages = [...currentMessages, message];
      setCurrentMessages(updatedMessages);
      saveMessages(currentThreadId, updatedMessages);

      // Update thread metadata
      setThreads((prev) =>
        prev.map((thread) => {
          if (thread.id === currentThreadId) {
            // If this is the first user message, update title
            const newTitle =
              thread.title === 'New Chat' && message.role === 'user'
                ? extractTitle(message.content)
                : thread.title;

            return {
              ...thread,
              title: newTitle,
              lastMessage: message.content,
              timestamp: message.timestamp,
              messageCount: updatedMessages.length,
            };
          }
          return thread;
        })
      );
    },
    [currentThreadId, currentMessages, saveMessages, setThreads]
  );

  // Update last message (for streaming)
  const updateLastMessage = useCallback(
    (message: ChatMessage) => {
      if (!currentThreadId) return;

      const updatedMessages = [...currentMessages];
      if (updatedMessages.length > 0) {
        updatedMessages[updatedMessages.length - 1] = message;
      } else {
        updatedMessages.push(message);
      }

      setCurrentMessages(updatedMessages);
      saveMessages(currentThreadId, updatedMessages);

      // Update thread metadata
      setThreads((prev) =>
        prev.map((thread) =>
          thread.id === currentThreadId
            ? {
                ...thread,
                lastMessage: message.content,
                timestamp: message.timestamp,
                messageCount: updatedMessages.length,
              }
            : thread
        )
      );
    },
    [currentThreadId, currentMessages, saveMessages, setThreads]
  );

  return {
    threads,
    currentThreadId,
    currentMessages,
    createThread,
    switchThread,
    deleteThread,
    updateThreadTitle,
    addMessage,
    updateLastMessage,
    isLoading,
    error,
  };
}
