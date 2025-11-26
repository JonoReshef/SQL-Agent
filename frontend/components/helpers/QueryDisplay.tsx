'use client';

import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { copyToClipboard } from '@/lib/utils';
import type { QueryExecution } from '@/types/interfaces';

interface QueryDisplayProps {
  queries: QueryExecution[];
  overallSummary?: string;
}

export function QueryDisplay({ queries, overallSummary }: QueryDisplayProps) {
  if (!queries || queries.length === 0) {
    return null;
  }

  return (
    <div className='space-y-3 mt-3'>
      {overallSummary && (
        <div className='bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4'>
          <div className='flex items-start space-x-2'>
            <svg
              className='w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0'
              fill='none'
              strokeLinecap='round'
              strokeLinejoin='round'
              strokeWidth='2'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path d='M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'></path>
            </svg>
            <div>
              <div className='text-sm font-semibold text-blue-900 mb-1'>
                Query Process Summary
              </div>
              <div className='text-sm text-blue-800'>{overallSummary}</div>
            </div>
          </div>
        </div>
      )}
      <div className='text-sm font-semibold text-gray-700'>
        SQL Queries Executed:
      </div>
      {queries.map((query, index) => (
        <QueryItem key={index} query={query} index={index} />
      ))}
    </div>
  );
}

interface QueryItemProps {
  query: QueryExecution;
  index: number;
}

function QueryItem({ query, index }: QueryItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(query.query);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className='border border-gray-300 rounded-lg overflow-hidden bg-white'>
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className='w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors'
      >
        <div className='flex-1 text-left'>
          <div className='text-sm font-medium text-gray-900'>
            Query {index + 1}
          </div>
          <div className='text-sm text-gray-600 mt-1'>{query.explanation}</div>
          {query.result_summary && (
            <div className='text-xs text-gray-500 mt-1'>
              {query.result_summary}
            </div>
          )}
        </div>
        <div className='ml-4'>
          <svg
            className={`w-5 h-5 text-gray-500 transition-transform ${
              isExpanded ? 'transform rotate-180' : ''
            }`}
            fill='none'
            strokeLinecap='round'
            strokeLinejoin='round'
            strokeWidth='2'
            viewBox='0 0 24 24'
            stroke='currentColor'
          >
            <path d='M19 9l-7 7-7-7'></path>
          </svg>
        </div>
      </button>

      {/* SQL Code - Expandable */}
      {isExpanded && (
        <div className='border-t border-gray-300'>
          <div className='relative'>
            <button
              onClick={handleCopy}
              className='absolute top-2 right-2 px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors'
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <SyntaxHighlighter
              language='sql'
              style={vscDarkPlus}
              customStyle={{
                margin: 0,
                borderRadius: 0,
                fontSize: '13px',
                padding: '1rem',
              }}
            >
              {query.query}
            </SyntaxHighlighter>
          </div>
        </div>
      )}
    </div>
  );
}
