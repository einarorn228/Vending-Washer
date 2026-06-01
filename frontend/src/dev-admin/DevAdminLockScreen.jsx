import React, { useState } from 'react';
import { storeDevAdminKey, unlockDevAdmin } from './api.js';

export default function DevAdminLockScreen({ onUnlocked }) {
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [isDisabled, setIsDisabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const key = password.trim();
    if (!key) {
      setMessage('Enter the kiosk API key to unlock this temporary beta panel.');
      return;
    }

    setIsLoading(true);
    setMessage('');
    setIsDisabled(false);
    const result = await unlockDevAdmin(key);
    setIsLoading(false);

    if (result.ok && result.payload?.success) {
      storeDevAdminKey(key);
      onUnlocked(key);
      return;
    }

    if (result.status === 403 || result.payload?.disabled) {
      setIsDisabled(true);
      setMessage(result.payload?.message || 'Beta dev/admin panel is disabled.');
      return;
    }

    setMessage(result.payload?.message || 'Wrong API key or backend is unreachable.');
  }

  return (
    <main className="dev-admin-lock">
      <section className="dev-admin-lock__card">
        <p className="dev-admin-eyebrow">Temporary beta tool</p>
        <h1>Beta Dev/Admin Panel</h1>
        <div className="dev-admin-warning" role="alert">
          Uses the kiosk API key as a temporary password. This is not production-grade security.
          Only use on trusted/local beta systems and disable <code>dev_admin_enabled</code> when done.
        </div>
        {isDisabled ? (
          <div className="dev-admin-disabled">
            <strong>Panel disabled.</strong> Enable backend setting <code>dev_admin_enabled=true</code> on the device before using this page.
          </div>
        ) : null}
        <form onSubmit={handleSubmit} className="dev-admin-lock__form">
          <label>
            API key / temporary password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="Enter API key"
            />
          </label>
          <button type="submit" disabled={isLoading}>{isLoading ? 'Unlocking…' : 'Unlock'}</button>
        </form>
        {message ? <p className="dev-admin-form-error">{message}</p> : null}
      </section>
    </main>
  );
}
