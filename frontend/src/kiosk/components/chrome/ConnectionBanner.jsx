import React from 'react';

export default function ConnectionBanner({ visible }) {
  if (!visible) {
    return null;
  }

  return (
    <div className="connection-banner" role="status" aria-live="polite">
      Backend connection lost. Check that the API is running, the API key is configured, and the
      /api proxy is available.
    </div>
  );
}
