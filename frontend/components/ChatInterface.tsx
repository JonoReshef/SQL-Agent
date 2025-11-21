'use client';

import { useState, useEffect, useRef } from 'react';
import { useChatThreads } from '@/hooks/useChatThreads';
import { useChatStream } from '@/hooks/useChatStream';
import { generateUUID } from '@/lib/utils';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessages } from './ChatMessages';
import { ChatInput } from './ChatInput';
import type { ChatMessage } from '@/types/interfaces';

export function ChatInterface() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const messageAddedRef = useRef(false);

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
    addMessage,
    updateLastMessage,
    isLoading,
  } = useChatThreads();

  const {
    sendMessage,
    isStreaming,
    currentResponse,
    queries,
    error,
    clearError,
  } = useChatStream();

  // Create initial thread if none exists
  useEffect(() => {
    if (threads.length === 0 && !currentThreadId) {
      createThread();
    }
  }, [threads.length, currentThreadId, createThread]);

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
    // Reset the flag for new message
    messageAddedRef.current = false;

    // Add user message
    const userMessage: ChatMessage = {
      id: generateUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    addMessage(userMessage);

    // Create placeholder for assistant message
    const assistantMessageId = generateUUID();

    try {
      // Send message and stream response
      await sendMessage(message, threadId);

      // Note: The streaming is handled by useChatStream hook
      // We need to watch currentResponse and queries to update the message
    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'system',
        content: `Error: ${error || 'Failed to send message'}`,
        timestamp: new Date(),
      };
      addMessage(errorMessage);
    }
  };

  // Update assistant message as streaming progresses
  useEffect(() => {
    if (!isStreaming && currentResponse && !messageAddedRef.current) {
      // Streaming complete, add the final assistant message (only once)
      const assistantMessage: ChatMessage = {
        id: generateUUID(),
        role: 'assistant',
        content: currentResponse,
        timestamp: new Date(),
        queries: queries.length > 0 ? queries : undefined,
      };

      // Always add as a new message (don't update)
      addMessage(assistantMessage);
      messageAddedRef.current = true;
    }
  }, [isStreaming, currentResponse, queries, addMessage]);

  // Display errors
  useEffect(() => {
    if (error) {
      const errorMessage: ChatMessage = {
        id: generateUUID(),
        role: 'system',
        content: `Error: ${error}`,
        timestamp: new Date(),
      };
      addMessage(errorMessage);
      clearError();
    }
  }, [error, addMessage, clearError]);

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
        isMobileOpen={isSidebarOpen}
        onMobileClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Chat Area */}
      <div className='flex-1 flex flex-col'>
        {/* Header */}
        <div className='bg-white border-b border-gray-300 px-4 py-4 flex items-center'>
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
              WestBrand SQL Chat
            </h1>
            <p className='text-sm text-gray-500'>
              Ask questions about your database in natural language
            </p>
          </div>
        </div>

        {/* Messages */}
        <ChatMessages messages={currentMessages} isStreaming={isStreaming} />

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
