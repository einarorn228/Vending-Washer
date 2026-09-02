import React, { useState } from 'react';
import { clearDevAdminKey, saveDevAdminSettings } from '../api.js';
import ContextualHelpLink from '../help/ContextualHelpLink.jsx';

export const LOCKOUT_CONFIRMATION_PHRASE = 'DISABLE DEV ADMIN';

const RECOVERY_COMMAND = `source .venv/bin/activate
python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value

session = Session()
try:
    update_setting_value(session, "dev_admin_enabled", "true")
finally:
    session.close()
PY`;

export default function DangerZonePanel({ apiKey, onLockedOut }) {
  const [phrase, setPhrase] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const phraseMatches = phrase.trim() === LOCKOUT_CONFIRMATION_PHRASE;

  async function handleDisable() {
    setSaving(true);
    setError('');
    const result = await saveDevAdminSettings(
      apiKey,
      { dev_admin_enabled: false },
      null,
      LOCKOUT_CONFIRMATION_PHRASE,
    );
    setSaving(false);
    if (!result.ok || !result.payload?.success) {
      setError(result.payload?.message || 'Could not disable the dev/admin panel.');
      return;
    }
    // The panel is now off for everyone; drop the local session so the UI cannot
    // pretend it still has access.
    clearDevAdminKey();
    onLockedOut();
  }

  return (
    <section className="dev-admin-panel dev-admin-panel--danger">
      <div className="dev-admin-panel__header">
        <div>
          <p className="dev-admin-eyebrow">Danger zone</p>
          <h2>Dev/Admin Access</h2>
        </div>
      </div>

      <div className="dev-admin-warning dev-admin-warning--danger">
        Turning the dev/admin panel off immediately locks this browser — and every other
        browser — out of <code>/dev/admin</code>. There is no way to switch it back on from
        this page. Someone must run the command below on the kiosk host.
      </div>

      <div className="dev-admin-setting">
        <div className="dev-admin-setting__meta">
          <label htmlFor="danger-zone-phrase">Disable the dev/admin panel</label>
          <p>
            Type <strong>{LOCKOUT_CONFIRMATION_PHRASE}</strong> to confirm you understand this
            locks you out.
          </p>
          <div className="dev-admin-badges">
            <span className="dev-admin-badge dev-admin-badge--high">risk: high</span>
            <span className="dev-admin-badge">applies immediately</span>
          </div>
        </div>
        <div className="dev-admin-setting__control">
          <input
            id="danger-zone-phrase"
            type="text"
            autoComplete="off"
            placeholder={LOCKOUT_CONFIRMATION_PHRASE}
            value={phrase}
            onChange={(event) => setPhrase(event.target.value)}
          />
          <button
            type="button"
            className="dev-admin-danger"
            style={{ marginTop: '0.5rem' }}
            disabled={!phraseMatches || saving}
            onClick={handleDisable}
          >
            {saving ? 'Disabling…' : 'Disable dev/admin panel'}
          </button>
          {error ? <p className="dev-admin-form-error">{error}</p> : null}
        </div>
      </div>

      <p>
        How to switch it back on: run this on the kiosk host, from the repository root.
        <ContextualHelpLink guideId="admin-access-recovery" label="Help: how to switch it back on" />
      </p>
      <div className="dev-admin-code-block">
        <pre><code>{RECOVERY_COMMAND}</code></pre>
      </div>
    </section>
  );
}
