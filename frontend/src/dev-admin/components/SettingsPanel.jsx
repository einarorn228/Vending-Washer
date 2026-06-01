import React, { useMemo, useState } from 'react';
import { saveDevAdminSettings } from '../api.js';
import SettingField from './SettingField.jsx';

function flattenSettings(groups) {
  const map = {};
  (groups || []).forEach((group) => {
    (group.settings || []).forEach((setting) => {
      map[setting.key] = setting.value;
    });
  });
  return map;
}

export default function SettingsPanel({ apiKey, groups, onReload }) {
  const initialValues = useMemo(() => flattenSettings(groups), [groups]);
  const [draft, setDraft] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    setDraft(initialValues);
    setErrors({});
  }, [initialValues]);

  function handleChange(key, value) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function changedValues() {
    const changes = {};
    Object.keys(draft).forEach((key) => {
      const before = initialValues[key];
      const after = draft[key];
      if (JSON.stringify(before) !== JSON.stringify(after)) {
        changes[key] = after;
      }
    });
    return changes;
  }

  async function handleSave() {
    const changes = changedValues();
    if (!Object.keys(changes).length) {
      setMessage('No setting changes to save.');
      return;
    }
    setSaving(true);
    setMessage('');
    setErrors({});
    const result = await saveDevAdminSettings(apiKey, changes);
    setSaving(false);
    if (!result.ok || !result.payload?.success) {
      setErrors(result.payload?.errors || {});
      setMessage(result.payload?.message || 'Settings save failed.');
      return;
    }
    setMessage('Settings saved. Reloading current values…');
    onReload();
  }

  return (
    <section className="dev-admin-panel">
      <div className="dev-admin-panel__header">
        <div>
          <p className="dev-admin-eyebrow">Whitelist editor</p>
          <h2>General Settings</h2>
        </div>
        <div className="dev-admin-actions">
          <button type="button" onClick={() => { setDraft(initialValues); setErrors({}); }}>Discard</button>
          <button type="button" className="dev-admin-primary" disabled={saving} onClick={handleSave}>{saving ? 'Saving…' : 'Save changed settings'}</button>
        </div>
      </div>
      <div className="dev-admin-warning">
        Secrets are read-only/masked in this beta. Risky settings are whitelist-based and validated by the backend before anything is written.
      </div>
      {(groups || []).map((group) => (
        <article key={group.id} className="dev-admin-group-card">
          <h3>{group.title}</h3>
          {(group.settings || []).map((setting) => (
            <SettingField
              key={setting.key}
              setting={setting}
              value={draft[setting.key]}
              error={errors[setting.key]}
              onChange={handleChange}
            />
          ))}
        </article>
      ))}
      {message ? <p className="dev-admin-save-message">{message}</p> : null}
    </section>
  );
}
