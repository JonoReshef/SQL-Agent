'use client';

import { useEffect, useRef } from 'react';
import { Message } from './helpers/Message';
import { QueryDisplay } from './helpers/QueryDisplay';
import { StreamingIndicator } from './helpers/StreamingIndicator';
import type { ChatMessage } from '@/types/interfaces';

interface ChatMessagesProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingStatus?: string;
}

export function ChatMessages({
  messages,
  isStreaming,
  streamingStatus,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className='flex-1 overflow-y-auto px-4 py-6 bg-gray-50'>
      {messages.length === 0 && !isStreaming && (
        <div className='h-full flex items-center justify-center text-gray-500'>
          <div className='text-center'>
            <svg
              className='mx-auto h-12 w-12 text-gray-400 mb-4'
              fill='none'
              strokeLinecap='round'
              strokeLinejoin='round'
              strokeWidth='2'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path d='M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z'></path>
            </svg>
            <p className='text-lg font-medium'>Start a conversation</p>
            <p className='text-sm mt-2'>
              Ask questions about your database in natural language
            </p>
          </div>
        </div>
      )}

      {messages.map((message) => (
        <div key={message.id}>
          <Message
            role={message.role}
            content={message.content}
            timestamp={message.timestamp}
            queries={message.queries}
            overallSummary={message.overallSummary}
          />
        </div>
      ))}

      {/* Streaming indicator */}
      {isStreaming && (
        <div className='mb-4'>
          <StreamingIndicator status={streamingStatus} />
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
