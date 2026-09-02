import React from 'react';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'remote_control', label: 'Remote Control' },
  { id: 'diagnostics', label: 'Diagnostics' },
  { id: 'settings', label: 'Settings' },
  { id: 'machines', label: 'Machine Cards' },
];

export const TAB_IDS = TABS.map((tab) => tab.id);

const RESTART_COMMAND = 'source .venv/bin/activate && python -m backend.app';

export default function DevAdminShell({
  activeTab,
  onTabChange,
  onLock,
  restartPending,
  onDismissRestart,
  children,
}) {
  return (
    <main className="dev-admin-page">
      <aside className="dev-admin-sidebar">
        <div>
          <p className="dev-admin-eyebrow">Temporary beta</p>
          <h1>Dev/Admin</h1>
          <p className="dev-admin-sidebar__copy">Trusted local beta controls. Not a production admin system.</p>
        </div>
        <nav className="dev-admin-nav" aria-label="Dev admin sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? 'is-active' : ''}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <button type="button" className="dev-admin-lock-button" onClick={onLock}>Lock panel</button>
      </aside>
      <section className="dev-admin-main">
        <div className="dev-admin-warning dev-admin-warning--top">
          Beta/dev admin panel. API-key lock is temporary and not production-grade security.
        </div>

        {restartPending?.length ? (
          <div className="dev-admin-warning dev-admin-warning--restart" role="status">
            <div>
              <strong>Restart required to apply:</strong> {restartPending.join(', ')}.
              <br />
              These values are saved, but the running backend is still using the old ones. On the
              kiosk host, from the repository root, stop the backend and start it again:
              <code className="dev-admin-inline-code">{RESTART_COMMAND}</code>
            </div>
            <button type="button" onClick={onDismissRestart}>Dismiss</button>
          </div>
        ) : null}

        {children}
      </section>
    </main>
  );
}
