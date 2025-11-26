'use client';

import { useState, useRef, useEffect } from 'react';
import { formatRelativeTime, truncate } from '@/lib/utils';
import type { Thread } from '@/types/interfaces';

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onClick: () => void;
  onDelete: () => void;
  onRename?: (newTitle: string) => void;
}

export function ThreadItem({
  thread,
  isActive,
  onClick,
  onDelete,
  onRename,
}: ThreadItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(thread.title);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(true);
    setEditTitle(thread.title);
  };

  const handleSaveEdit = () => {
    const trimmedTitle = editTitle.trim();
    if (trimmedTitle && trimmedTitle !== thread.title && onRename) {
      onRename(trimmedTitle);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditTitle(thread.title);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div
      className={`group relative px-4 py-3 cursor-pointer transition-colors ${
        isActive
          ? 'bg-primary-100 border-l-4 border-primary-600'
          : 'hover:bg-gray-100 border-l-4 border-transparent'
      }`}
      onClick={isEditing ? undefined : onClick}
    >
      <div className='flex items-start justify-between'>
        <div className='flex-1 min-w-0'>
          {isEditing ? (
            <input
              ref={inputRef}
              type='text'
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={handleSaveEdit}
              onKeyDown={handleKeyDown}
              onClick={(e) => e.stopPropagation()}
              className='text-sm font-medium w-full px-2 py-1 border border-primary-500 rounded focus:outline-none focus:ring-2 focus:ring-primary-500'
              maxLength={100}
            />
          ) : (
            <div
              className={`text-sm font-medium truncate ${
                isActive ? 'text-primary-900' : 'text-gray-900'
              }`}
            >
              {thread.title}
            </div>
          )}
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

        {/* Action buttons - shows on hover */}
        <div className='flex items-center space-x-1 ml-2'>
          {!isEditing && onRename && (
            <button
              onClick={handleStartEdit}
              className='opacity-0 group-hover:opacity-100 p-1 hover:bg-blue-100 rounded transition-all'
              aria-label='Edit thread title'
            >
              <svg
                className='w-4 h-4 text-blue-600'
                fill='none'
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth='2'
                viewBox='0 0 24 24'
                stroke='currentColor'
              >
                <path d='M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'></path>
              </svg>
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className='opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all'
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
    </div>
  );
}
