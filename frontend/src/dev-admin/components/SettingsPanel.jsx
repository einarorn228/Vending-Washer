import React, { useMemo, useState } from 'react';
import { saveDevAdminSettings } from '../api.js';
import SettingField from './SettingField.jsx';
import SecuritySettingsPanel from './SecuritySettingsPanel.jsx';
import ChangeReviewModal from './ChangeReviewModal.jsx';
import DangerZonePanel from './DangerZonePanel.jsx';

// dev_admin_enabled is handled by DangerZonePanel, never as a casual toggle here.
const DANGER_ZONE_KEYS = new Set(['dev_admin_enabled']);

function flattenSettings(groups) {
  const map = {};
  (groups || []).forEach((group) => {
    (group.settings || []).forEach((setting) => {
      map[setting.key] = setting.value;
    });
  });
  return map;
}

function settingsByKey(groups) {
  const map = {};
  (groups || []).forEach((group) => {
    (group.settings || []).forEach((setting) => {
      map[setting.key] = setting;
    });
  });
  return map;
}

function parseDefault(setting) {
  const raw = setting.default;
  if (raw === null || raw === undefined) return '';
  if (setting.type === 'bool') return String(raw).toLowerCase() === 'true';
  if (setting.type === 'int') return Number.parseInt(raw, 10);
  if (setting.type === 'float') return Number.parseFloat(raw);
  if (setting.type === 'list') {
    return String(raw)
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return raw;
}

export default function SettingsPanel({ apiKey, groups, secretMetadata, onReload, onLockedOut, onRestartRequired }) {
  const initialValues = useMemo(() => flattenSettings(groups), [groups]);
  const metaByKey = useMemo(() => settingsByKey(groups), [groups]);
  const [draft, setDraft] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState('');
  const [changedOnly, setChangedOnly] = useState(false);
  const [reviewChanges, setReviewChanges] = useState(null);

  React.useEffect(() => {
    setDraft((current) => {
      // Keep unsaved edits across a background status refresh; only adopt server
      // values for fields the operator has not touched.
      const next = { ...initialValues };
      Object.keys(current).forEach((key) => {
        if (JSON.stringify(current[key]) !== JSON.stringify(initialValues[key])) {
          next[key] = current[key];
        }
      });
      return next;
    });
  }, [initialValues]);

  function handleChange(key, value) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function handleReset(key) {
    const setting = metaByKey[key];
    if (!setting) return;
    handleChange(key, parseDefault(setting));
  }

  function changedValues() {
    const changes = {};
    Object.keys(draft).forEach((key) => {
      if (DANGER_ZONE_KEYS.has(key)) return;
      if (JSON.stringify(initialValues[key]) !== JSON.stringify(draft[key])) {
        changes[key] = draft[key];
      }
    });
    return changes;
  }

  const pendingChanges = changedValues();
  const pendingCount = Object.keys(pendingChanges).length;

  function openReview() {
    if (!pendingCount) {
      setMessage('No setting changes to save.');
      return;
    }
    setMessage('');
    setReviewChanges(
      Object.keys(pendingChanges).map((key) => ({
        key,
        label: metaByKey[key]?.label || key,
        risk: metaByKey[key]?.risk || 'low',
        restartRequired: Boolean(metaByKey[key]?.restart_required),
        previous: initialValues[key],
        next: pendingChanges[key],
      })),
    );
  }

  async function handleConfirmedSave() {
    setSaving(true);
    setErrors({});
    const result = await saveDevAdminSettings(apiKey, pendingChanges);
    setSaving(false);
    if (!result.ok || !result.payload?.success) {
      setReviewChanges(null);
      setErrors(result.payload?.errors || {});
      setMessage(result.payload?.message || 'Settings save failed.');
      return;
    }
    const restartKeys = (result.payload.updated || [])
      .filter((entry) => entry.restart_required)
      .map((entry) => metaByKey[entry.key]?.label || entry.key);
    if (restartKeys.length) {
      onRestartRequired(restartKeys);
    }
    setReviewChanges(null);
    setMessage('Settings saved. Reloading current values…');
    onReload();
  }

  const needle = filter.trim().toLowerCase();
  const visibleGroups = (groups || [])
    .map((group) => ({
      ...group,
      settings: (group.settings || []).filter((setting) => {
        if (DANGER_ZONE_KEYS.has(setting.key)) return false;
        if (changedOnly && JSON.stringify(initialValues[setting.key]) === JSON.stringify(draft[setting.key])) {
          return false;
        }
        if (!needle) return true;
        return (
          setting.key.toLowerCase().includes(needle) ||
          (setting.label || '').toLowerCase().includes(needle) ||
          (setting.description || '').toLowerCase().includes(needle)
        );
      }),
    }))
    .filter((group) => group.settings.length > 0);

  return (
    <section className="dev-admin-panel">
      <div className="dev-admin-panel__header">
        <div>
          <p className="dev-admin-eyebrow">Whitelist editor</p>
          <h2>General Settings</h2>
        </div>
        <div className="dev-admin-actions">
          <button type="button" onClick={() => { setDraft(initialValues); setErrors({}); setMessage(''); }}>
            Discard
          </button>
          <button type="button" className="dev-admin-primary" disabled={saving || !pendingCount} onClick={openReview}>
            {pendingCount ? `Review ${pendingCount} change${pendingCount === 1 ? '' : 's'}` : 'No changes'}
          </button>
        </div>
      </div>

      <div className="dev-admin-warning">
        Secrets are read-only/masked in this beta. Risky settings are whitelist-based and validated by the backend before anything is written.
      </div>

      <div className="dev-admin-filter-row">
        <input
          type="search"
          className="dev-admin-filter"
          placeholder="Filter settings by name or description…"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          aria-label="Filter settings"
        />
        <label className="dev-admin-toggle-row">
          <input type="checkbox" checked={changedOnly} onChange={(event) => setChangedOnly(event.target.checked)} />
          Changed only
        </label>
      </div>

      {visibleGroups.length === 0 ? (
        <p className="dev-admin-save-message">No settings match this filter.</p>
      ) : null}

      {visibleGroups.map((group) => (
        <article key={group.id} className="dev-admin-group-card">
          <h3>{group.title}</h3>
          {group.settings.map((setting) => (
            <SettingField
              key={setting.key}
              setting={setting}
              value={draft[setting.key]}
              error={errors[setting.key]}
              isChanged={JSON.stringify(initialValues[setting.key]) !== JSON.stringify(draft[setting.key])}
              onChange={handleChange}
              onReset={handleReset}
            />
          ))}
        </article>
      ))}

      <SecuritySettingsPanel
        authKey={apiKey}
        reisaTokenIsSet={secretMetadata?.reisa_bearer_token_set}
      />

      <DangerZonePanel apiKey={apiKey} onLockedOut={onLockedOut} />

      {message ? <p className="dev-admin-save-message">{message}</p> : null}

      {reviewChanges ? (
        <ChangeReviewModal
          changes={reviewChanges}
          saving={saving}
          onCancel={() => setReviewChanges(null)}
          onConfirm={handleConfirmedSave}
        />
      ) : null}
    </section>
  );
}
