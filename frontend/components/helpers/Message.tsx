'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { MessageRole, QueryExecution } from '@/types/interfaces';
import { formatTimestamp } from '@/lib/utils';
import { QueryDisplay } from './QueryDisplay';

interface MessageProps {
  role: MessageRole;
  content: string;
  timestamp: Date | string;
  queries?: QueryExecution[];
  overallSummary?: string;
}

export function Message({
  role,
  content,
  timestamp,
  queries,
  overallSummary,
}: MessageProps) {
  const [showDetails, setShowDetails] = useState(false);
  const isUser = role === 'user';
  const isSystem = role === 'system';
  const hasQueries = queries && queries.length > 0;

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 group`}
    >
      <div className='max-w-[80%]'>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-primary-600 text-white'
              : isSystem
                ? 'bg-gray-200 text-gray-700 italic'
                : 'bg-gray-100 text-gray-900'
          }`}
        >
          <div className='prose prose-sm max-w-none break-words'>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
          <div
            className={`text-xs mt-2 flex items-center justify-between ${
              isUser ? 'text-primary-100' : 'text-gray-500'
            }`}
          >
            <span>{formatTimestamp(timestamp)}</span>
            {hasQueries && !isUser && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className='ml-4 text-xs underline hover:no-underline'
              >
                {showDetails ? 'Hide Details' : 'Show Details'}
              </button>
            )}
          </div>
        </div>
        {/* Collapsible query details */}
        {hasQueries && showDetails && (
          <div className='mt-2'>
            <QueryDisplay queries={queries} overallSummary={overallSummary} />
          </div>
        )}
      </div>
    </div>
  );
}
