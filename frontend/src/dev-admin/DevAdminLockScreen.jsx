import React, { useState } from 'react';
import { storeDevAdminKey, unlockDevAdmin } from './api.js';

export default function DevAdminLockScreen({ onUnlocked }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [isDisabled, setIsDisabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const user = username.trim();
    const pass = password.trim();
    if (!user || !pass) {
      setMessage('Enter your username and password to unlock this admin panel.');
      return;
    }

    const authKey = btoa(`${user}:${pass}`);

    setIsLoading(true);
    setMessage('');
    setIsDisabled(false);
    const result = await unlockDevAdmin(authKey);
    setIsLoading(false);

    if (result.ok && result.payload?.success) {
      storeDevAdminKey(user, pass);
      onUnlocked(authKey);
      return;
    }

    if (result.status === 403 || result.payload?.disabled) {
      setIsDisabled(true);
      setMessage(result.payload?.message || 'Beta dev/admin panel is disabled.');
      return;
    }

    setMessage(result.payload?.message || 'Wrong credentials or backend is unreachable.');
  }

  return (
    <main className="dev-admin-lock">
      <section className="dev-admin-lock__card">
        <p className="dev-admin-eyebrow">Administration</p>
        <h1>Dev/Admin Panel</h1>
        <div className="dev-admin-warning" role="alert">
          Please log in with your administrative credentials.
        </div>
        {isDisabled ? (
          <div className="dev-admin-disabled">
            <strong>Panel disabled.</strong> Enable backend setting <code>dev_admin_enabled=true</code> on the device before using this page.
          </div>
        ) : null}
        <form onSubmit={handleSubmit} className="dev-admin-lock__form">
          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              placeholder="Enter username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="Enter password"
            />
          </label>
          <button type="submit" disabled={isLoading}>{isLoading ? 'Unlocking…' : 'Unlock'}</button>
        </form>
        {message ? <p className="dev-admin-form-error">{message}</p> : null}
      </section>
    </main>
  );
}
