import React from 'react';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'settings', label: 'Settings' },
  { id: 'machines', label: 'Machine Cards' },
];

export default function DevAdminShell({ activeTab, onTabChange, onLock, children }) {
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
        {children}
      </section>
    </main>
  );
}
