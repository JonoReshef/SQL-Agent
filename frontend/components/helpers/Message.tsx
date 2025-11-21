'use client';

import type { MessageRole } from '@/types/interfaces';
import { formatTimestamp } from '@/lib/utils';

interface MessageProps {
  role: MessageRole;
  content: string;
  timestamp: Date;
}

export function Message({ role, content, timestamp }: MessageProps) {
  const isUser = role === 'user';
  const isSystem = role === 'system';

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 group`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-primary-600 text-white'
            : isSystem
              ? 'bg-gray-200 text-gray-700 italic'
              : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className='whitespace-pre-wrap break-words'>{content}</div>
        <div
          className={`text-xs mt-2 ${
            isUser ? 'text-primary-100' : 'text-gray-500'
          }`}
        >
          {formatTimestamp(timestamp)}
        </div>
      </div>
    </div>
  );
}
