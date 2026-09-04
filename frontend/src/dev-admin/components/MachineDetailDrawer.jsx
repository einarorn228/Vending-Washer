import React, { useState } from 'react';
import { saveDevAdminMachine } from '../api.js';
import ContextualHelpLink from '../help/ContextualHelpLink.jsx';

// Must stay identical to SELECTABLE_METRIC_SOURCES in backend/controllers/telemetry.py.
// backend/tests/test_telemetry_metric_contract.py fails if these drift apart.
const METRIC_SOURCES = ['none', 'voltage', 'power', 'digital'];

export default function MachineDetailDrawer({ apiKey, machine, onClose, onSaved }) {
  const [technical, setTechnical] = useState(() => ({ ...(machine?.technical || {}) }));
  const [confirmHighRisk, setConfirmHighRisk] = useState(false);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  if (!machine) return null;

  function setField(field, value) {
    setTechnical((current) => ({ ...current, [field]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setErrors({});
    setMessage('');
    const result = await saveDevAdminMachine(apiKey, machine.machine_key, {
      technical,
      confirm_high_risk: confirmHighRisk,
    });
    setSaving(false);
    if (!result.ok || !result.payload?.success) {
      setErrors(result.payload?.errors || {});
      setMessage(result.payload?.message || 'Technical mapping save failed.');
      return;
    }
    setMessage('Advanced technical mapping saved.');
    onSaved();
  }

  function err(name) {
    return errors[`technical.${name}`] || errors[name];
  }

  return (
    <div className="dev-admin-drawer__overlay" role="presentation" onClick={onClose}>
      <aside className="dev-admin-drawer" role="dialog" aria-modal="true" aria-labelledby="machine-detail-title" onClick={(event) => event.stopPropagation()}>
        <header className="dev-admin-drawer__header">
          <div>
            <p className="dev-admin-eyebrow">Advanced / Technical Mapping</p>
            <h2 id="machine-detail-title">
              {machine.display_name}
              <ContextualHelpLink
                guideId="machine-technical-mapping"
                label="Help: technical mapping"
                machineId={machine.machine_key}
              />
            </h2>
          </div>
          <button type="button" onClick={onClose}>✕</button>
        </header>

        <div className="dev-admin-warning dev-admin-warning--danger">
          Wrong Shelly IPs, relay channels, I4 button indexes, metric sources, or telemetry thresholds can start the wrong physical washer/dryer or break availability reporting. These fields never autosave.
        </div>

        <div className="dev-admin-readonly-grid">
          <span>Internal key</span><strong>{machine.machine_key}</strong>
          <span>Database ID</span><strong>{machine.id}</strong>
          <span>UNI device</span><strong>{technical.uni_device_name || technical.uni_device_id || 'unknown'}</strong>
          <span>I4 device</span><strong>{technical.i4_device_name || technical.i4_device_id || 'none'}</strong>
        </div>

        <div className="dev-admin-technical-grid">
          <label>Shelly IP<input value={technical.shelly_ip ?? ''} onChange={(e) => setField('shelly_ip', e.target.value)} />{err('shelly_ip') ? <span>{err('shelly_ip')}</span> : null}</label>
          <label>Relay channel<input type="number" value={technical.relay_channel ?? ''} onChange={(e) => setField('relay_channel', e.target.value)} />{err('relay_channel') ? <span>{err('relay_channel')}</span> : null}</label>
          <label>I4 button index<input type="number" value={technical.i4_button_index ?? ''} onChange={(e) => setField('i4_button_index', e.target.value)} />{err('i4_button_index') ? <span>{err('i4_button_index')}</span> : null}</label>
          <label>Metric source<select value={technical.metric_source ?? 'none'} onChange={(e) => setField('metric_source', e.target.value)}>{METRIC_SOURCES.map((source) => <option key={source} value={source}>{source}</option>)}</select>{err('metric_source') ? <span>{err('metric_source')}</span> : null}</label>
          <label>On threshold<input type="number" value={technical.on_threshold ?? ''} onChange={(e) => setField('on_threshold', e.target.value)} />{err('on_threshold') ? <span>{err('on_threshold')}</span> : null}</label>
          <label>Off threshold<input type="number" value={technical.off_threshold ?? ''} onChange={(e) => setField('off_threshold', e.target.value)} />{err('off_threshold') ? <span>{err('off_threshold')}</span> : null}</label>
          <label>On confirm ms<input type="number" value={technical.on_confirm_ms ?? ''} onChange={(e) => setField('on_confirm_ms', e.target.value)} />{err('on_confirm_ms') ? <span>{err('on_confirm_ms')}</span> : null}</label>
          <label>Off confirm ms<input type="number" value={technical.off_confirm_ms ?? ''} onChange={(e) => setField('off_confirm_ms', e.target.value)} />{err('off_confirm_ms') ? <span>{err('off_confirm_ms')}</span> : null}</label>
          <label>Poll interval ms<input type="number" value={technical.poll_interval_ms ?? ''} onChange={(e) => setField('poll_interval_ms', e.target.value)} />{err('poll_interval_ms') ? <span>{err('poll_interval_ms')}</span> : null}</label>
        </div>

        <label className="dev-admin-confirm">
          <input type="checkbox" checked={confirmHighRisk} onChange={(event) => setConfirmHighRisk(event.target.checked)} />
          I understand these changes can start the wrong physical machine or break machine availability if configured incorrectly.
        </label>
        {errors.confirm_high_risk ? <p className="dev-admin-form-error">{errors.confirm_high_risk}</p> : null}
        {message ? <p className="dev-admin-save-message">{message}</p> : null}
        <footer className="dev-admin-drawer__actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="dev-admin-primary" disabled={!confirmHighRisk || saving} onClick={handleSave}>{saving ? 'Saving…' : 'Save advanced changes'}</button>
        </footer>
      </aside>
    </div>
  );
}
