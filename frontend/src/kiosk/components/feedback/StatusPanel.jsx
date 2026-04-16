import React from 'react';

export default function StatusPanel({ title, children }) {
  return (
    <section className="status-panel" aria-live="polite">
      {title ? <h2 className="status-panel__title">{title}</h2> : null}
      <div className="status-panel__content">{children}</div>
    </section>
  );
}
