'use client';

import { useState, useEffect, useRef } from 'react';
import { useChatThreads } from '@/hooks/useChatThreads';
import { useChatStream } from '@/hooks/useChatStream';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessages } from './ChatMessages';
import { ChatInput } from './ChatInput';
import type { ChatMessage } from '@/types/interfaces';

export function ChatInterface() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [anticipateComplexity, setAnticipateComplexity] = useState(false);
  const streamingMessageIdRef = useRef<string | null>(null);
  const pendingMessageRef = useRef<string | null>(null);

  // Prevent hydration errors by only rendering client-specific code after mount
  useEffect(() => {
    setIsClient(true);
  }, []);

  const {
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
  } = useChatThreads();

  const {
    sendMessage,
    isStreaming,
    streamingThreadId,
    currentResponse,
    currentStatus,
    queries,
    overallSummary,
    error,
    clearError,
    userMessageId,
    assistantMessageId,
    threadTitle,
  } = useChatStream();

  // Create initial thread if none exists (only after init completes)
  useEffect(() => {
    if (isInitialised && threads.length === 0 && !currentThreadId) {
      createThread();
    }
  }, [isInitialised, threads.length, currentThreadId, createThread]);

  const handleSendMessage = async (message: string) => {
    if (!currentThreadId) {
      const newThreadId = createThread();
      return handleSendMessageToThread(message, newThreadId);
    }
    return handleSendMessageToThread(message, currentThreadId);
  };

  const handleSendMessageToThread = async (
    message: string,
    threadId: string
  ) => {
    // Store the pending message text so we can create the ChatMessage
    // once the backend confirms with user_message_created event
    pendingMessageRef.current = message;
    streamingMessageIdRef.current = null;

    try {
      await sendMessage(message, threadId, anticipateComplexity);
    } catch (err) {
      console.error('Error sending message:', err);
    }
  };

  // When backend confirms user message was created, add it to the originating thread
  useEffect(() => {
    if (userMessageId && pendingMessageRef.current && streamingThreadId) {
      const userMessage: ChatMessage = {
        id: userMessageId,
        role: 'user',
        content: pendingMessageRef.current,
        timestamp: new Date(),
        status: 'complete',
      };
      addMessage(streamingThreadId, userMessage);
      pendingMessageRef.current = null;
    }
  }, [userMessageId, streamingThreadId, addMessage]);

  // When backend confirms assistant placeholder, add it to the originating thread
  useEffect(() => {
    if (assistantMessageId && streamingThreadId) {
      streamingMessageIdRef.current = assistantMessageId;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        status: 'streaming',
      };
      addMessage(streamingThreadId, assistantMessage);
    }
  }, [assistantMessageId, streamingThreadId, addMessage]);

  // When backend provides a thread title, update the originating thread metadata
  useEffect(() => {
    if (threadTitle && streamingThreadId) {
      updateThreadMetadata(streamingThreadId, { title: threadTitle });
    }
  }, [threadTitle, streamingThreadId, updateThreadMetadata]);

  // Update streaming message by ID as content arrives
  useEffect(() => {
    const messageId = streamingMessageIdRef.current;
    if (messageId && currentResponse && streamingThreadId) {
      updateMessageById(streamingThreadId, messageId, {
        content: currentResponse,
        status: isStreaming ? 'streaming' : 'complete',
        queries: !isStreaming && queries.length > 0 ? queries : undefined,
        overallSummary:
          !isStreaming && overallSummary ? overallSummary : undefined,
      });

      // Clear ref when streaming completes
      if (!isStreaming) {
        streamingMessageIdRef.current = null;
      }
    }
  }, [
    currentResponse,
    isStreaming,
    queries,
    overallSummary,
    streamingThreadId,
    updateMessageById,
  ]);

  // Display errors in the current thread (not scoped to streaming thread)
  useEffect(() => {
    if (error && currentThreadId) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'system',
        content: `Error: ${error}`,
        timestamp: new Date(),
        status: 'complete',
      };
      addMessage(currentThreadId, errorMessage);
      clearError();
    }
  }, [error, currentThreadId, addMessage, clearError]);

  // Prevent hydration errors - only render after client mount
  if (!isClient) {
    return (
      <div className='h-screen flex items-center justify-center'>
        <div className='text-gray-500'>Loading...</div>
      </div>
    );
  }

  return (
    <div className='h-screen flex'>
      {/* Sidebar */}
      <ChatSidebar
        threads={threads}
        currentThreadId={currentThreadId}
        onCreateThread={createThread}
        onSwitchThread={switchThread}
        onDeleteThread={deleteThread}
        onClearAllThreads={clearAllThreads}
        onRenameThread={updateThreadTitle}
        isMobileOpen={isSidebarOpen}
        onMobileClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Chat Area */}
      <div className='flex-1 flex flex-col'>
        {/* Header */}
        <div className='bg-white border-b border-gray-300 px-4 py-4 flex items-center justify-between'>
          <div className='flex items-center'>
            <button
              onClick={() => setIsSidebarOpen(true)}
              className='md:hidden mr-3 p-2 hover:bg-gray-100 rounded'
              aria-label='Open sidebar'
            >
              <svg
                className='w-6 h-6'
                fill='none'
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth='2'
                viewBox='0 0 24 24'
                stroke='currentColor'
              >
                <path d='M4 6h16M4 12h16M4 18h16'></path>
              </svg>
            </button>
            <div>
              <h1 className='text-xl font-semibold text-gray-900'>
                Westbrand Product & Inventory Chat
              </h1>
              <p className='text-sm text-gray-500'>
                Ask questions about your data in natural language
              </p>
            </div>
          </div>

          {/* Complexity Toggle */}
          <div className='flex items-center space-x-3'>
            <label className='flex items-center cursor-pointer group'>
              <span
                className={`text-sm mr-3 transition-colors ${
                  anticipateComplexity
                    ? 'text-primary-600 font-medium'
                    : 'text-gray-600'
                }`}
              >
                {anticipateComplexity ? 'Thorough' : 'Quick'}
              </span>
              <div className='relative'>
                <input
                  type='checkbox'
                  className='sr-only'
                  checked={anticipateComplexity}
                  onChange={(e) => setAnticipateComplexity(e.target.checked)}
                />
                <div
                  className={`w-11 h-6 rounded-full transition-colors ${
                    anticipateComplexity ? 'bg-primary-600' : 'bg-gray-300'
                  }`}
                ></div>
                <div
                  className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                    anticipateComplexity ? 'transform translate-x-5' : ''
                  }`}
                ></div>
              </div>
            </label>
          </div>
        </div>

        {/* Messages — only show streaming UI if this is the thread being streamed */}
        <ChatMessages
          messages={currentMessages}
          isStreaming={isStreaming && currentThreadId === streamingThreadId}
          streamingStatus={isStreaming && currentThreadId === streamingThreadId ? currentStatus : undefined}
        />

        {/* Input */}
        <ChatInput
          onSubmit={handleSendMessage}
          disabled={isStreaming || isLoading}
          placeholder='Ask a question about your database...'
        />
      </div>
    </div>
  );
}
