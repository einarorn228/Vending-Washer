import React from 'react';

export default function MachineIcon({ type, className = '' }) {
  if (type === 'washer') {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect width="14" height="19" x="5" y="3" rx="2" />
        <path d="M5 8h14" />
        <circle cx="16" cy="5.5" r="1" fill="currentColor" stroke="none" />
        <circle cx="13" cy="5.5" r="0.5" fill="currentColor" stroke="none" />
        <circle cx="12" cy="15" r="4.5" />
        <path d="M9 16.5c1.5-1 4.5-1 6 0" opacity="0.5" />
      </svg>
    );
  }

  // dryer
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
      <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
      <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
    </svg>
  );
}
