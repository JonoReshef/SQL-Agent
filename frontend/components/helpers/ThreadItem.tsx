'use client';

import { formatRelativeTime, truncate } from '@/lib/utils';
import type { Thread } from '@/types/interfaces';

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onClick: () => void;
  onDelete: () => void;
}

export function ThreadItem({
  thread,
  isActive,
  onClick,
  onDelete,
}: ThreadItemProps) {
  return (
    <div
      className={`group relative px-4 py-3 cursor-pointer transition-colors ${
        isActive
          ? 'bg-primary-100 border-l-4 border-primary-600'
          : 'hover:bg-gray-100 border-l-4 border-transparent'
      }`}
      onClick={onClick}
    >
      <div className='flex items-start justify-between'>
        <div className='flex-1 min-w-0'>
          <div
            className={`text-sm font-medium truncate ${
              isActive ? 'text-primary-900' : 'text-gray-900'
            }`}
          >
            {thread.title}
          </div>
          {thread.lastMessage && (
            <div className='text-xs text-gray-500 truncate mt-1'>
              {truncate(thread.lastMessage, 60)}
            </div>
          )}
          <div className='text-xs text-gray-400 mt-1'>
            {formatRelativeTime(thread.timestamp)} • {thread.messageCount}{' '}
            {thread.messageCount === 1 ? 'message' : 'messages'}
          </div>
        </div>

        {/* Delete button - shows on hover */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className='opacity-0 group-hover:opacity-100 ml-2 p-1 hover:bg-red-100 rounded transition-all'
          aria-label='Delete thread'
        >
          <svg
            className='w-4 h-4 text-red-600'
            fill='none'
            strokeLinecap='round'
            strokeLinejoin='round'
            strokeWidth='2'
            viewBox='0 0 24 24'
            stroke='currentColor'
          >
            <path d='M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16'></path>
          </svg>
        </button>
      </div>
    </div>
  );
}
