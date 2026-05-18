import React from 'react';

import { isApiKeyConfigured } from '../../../api/backend.js';

export default function ConnectionBanner({ visible }) {
  if (!visible && isApiKeyConfigured()) {
    return null;
  }

  const missingKeyBanner = !isApiKeyConfigured() ? (
    <div className="connection-banner connection-banner--missing-key" role="status" aria-live="polite">
      Enginn API lykill í þessum vafra. Bættu við{' '}
      <code>VITE_API_KEY</code> í skrána <code>frontend/.env</code> og endurræstu Vite.
    </div>
  ) : null;

  const unreachableBanner = (isApiKeyConfigured() && visible) ? (
    <div className="connection-banner connection-banner--unreachable" role="status" aria-live="polite">
      Backend connection lost. Check that the API is running, the API key is configured, and the
      /api proxy is available.
    </div>
  ) : null;

  return (
    <>
      {missingKeyBanner}
      {unreachableBanner}
    </>
  );
}
