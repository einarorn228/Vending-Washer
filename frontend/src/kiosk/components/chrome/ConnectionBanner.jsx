import React from 'react';

export default function ConnectionBanner({ visible }) {
  if (!visible) {
    return null;
  }

  return (
    <div className="connection-banner" role="status" aria-live="polite">
      Ekki náð í bakenda (API / net). Athugaðu að Flask keyri á port 5000, réttan{' '}
      <code>VITE_API_KEY</code> eða <code>localStorage API_KEY</code>, og að <code>/api</code> sé
      proxy-að í Vite.
    </div>
  );
}
