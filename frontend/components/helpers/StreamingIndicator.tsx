'use client';

export function StreamingIndicator() {
  return (
    <div className='flex items-center space-x-2 text-gray-600'>
      <div className='flex space-x-1'>
        <div className='w-2 h-2 bg-primary-600 rounded-full animate-bounce'></div>
        <div
          className='w-2 h-2 bg-primary-600 rounded-full animate-bounce'
          style={{ animationDelay: '0.1s' }}
        ></div>
        <div
          className='w-2 h-2 bg-primary-600 rounded-full animate-bounce'
          style={{ animationDelay: '0.2s' }}
        ></div>
      </div>
      <span className='text-sm'>Agent is thinking...</span>
    </div>
  );
}
