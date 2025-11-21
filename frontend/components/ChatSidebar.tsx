'use client';

import { useState } from 'react';
import { ThreadItem } from './helpers/ThreadItem';
import type { Thread } from '@/types/interfaces';

interface ChatSidebarProps {
  threads: Thread[];
  currentThreadId: string | null;
  onCreateThread: () => void;
  onSwitchThread: (threadId: string) => void;
  onDeleteThread: (threadId: string) => void;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

export function ChatSidebar({
  threads,
  currentThreadId,
  onCreateThread,
  onSwitchThread,
  onDeleteThread,
  isMobileOpen,
  onMobileClose,
}: ChatSidebarProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const handleDelete = (threadId: string) => {
    if (deleteConfirm === threadId) {
      onDeleteThread(threadId);
      setDeleteConfirm(null);
      onMobileClose(); // Close sidebar on mobile after deletion
    } else {
      setDeleteConfirm(threadId);
      setTimeout(() => setDeleteConfirm(null), 3000); // Reset after 3 seconds
    }
  };

  const handleSwitchThread = (threadId: string) => {
    onSwitchThread(threadId);
    onMobileClose(); // Close sidebar on mobile after switching
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className='fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden'
          onClick={onMobileClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:relative inset-y-0 left-0 z-50 w-80 bg-white border-r border-gray-300 flex flex-col transform transition-transform duration-300 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        {/* Header */}
        <div className='p-4 border-b border-gray-300 flex items-center justify-between'>
          <h2 className='text-lg font-semibold text-gray-900'>Chat History</h2>
          <button
            onClick={onMobileClose}
            className='md:hidden p-2 hover:bg-gray-100 rounded'
            aria-label='Close sidebar'
          >
            <svg
              className='w-5 h-5'
              fill='none'
              strokeLinecap='round'
              strokeLinejoin='round'
              strokeWidth='2'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path d='M6 18L18 6M6 6l12 12'></path>
            </svg>
          </button>
        </div>

        {/* New Chat Button */}
        <div className='p-4'>
          <button
            onClick={() => {
              onCreateThread();
              onMobileClose();
            }}
            className='w-full px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium flex items-center justify-center space-x-2'
          >
            <svg
              className='w-5 h-5'
              fill='none'
              strokeLinecap='round'
              strokeLinejoin='round'
              strokeWidth='2'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path d='M12 4v16m8-8H4'></path>
            </svg>
            <span>New Chat</span>
          </button>
        </div>

        {/* Thread List */}
        <div className='flex-1 overflow-y-auto'>
          {threads.length === 0 ? (
            <div className='p-4 text-center text-gray-500 text-sm'>
              No conversations yet. Start a new chat!
            </div>
          ) : (
            <div>
              {threads.map((thread) => (
                <div key={thread.id} className='relative'>
                  <ThreadItem
                    thread={thread}
                    isActive={thread.id === currentThreadId}
                    onClick={() => handleSwitchThread(thread.id)}
                    onDelete={() => handleDelete(thread.id)}
                  />
                  {deleteConfirm === thread.id && (
                    <div className='absolute inset-0 bg-red-500 bg-opacity-90 flex items-center justify-center text-white text-sm font-medium'>
                      Click again to confirm delete
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className='p-4 border-t border-gray-300 text-xs text-gray-500'>
          WestBrand SQL Chat Agent v1.0
        </div>
      </div>
    </>
  );
}
