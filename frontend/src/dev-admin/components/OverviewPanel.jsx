import React, { useState } from 'react';
import { exportDevAdminConfig } from '../api.js';

function StatusItem({ label, value, tone }) {
  return (
    <div className="dev-admin-status-item">
      <span>{label}</span>
      <strong className={tone ? `tone-${tone}` : ''}>{String(value)}</strong>
    </div>
  );
}

export default function OverviewPanel({ apiKey, status, onReload }) {
  const [exportMessage, setExportMessage] = useState('');

  async function handleExport() {
    setExportMessage('Preparing export…');
    const result = await exportDevAdminConfig(apiKey);
    if (!result.ok || !result.payload?.success) {
      setExportMessage(result.payload?.message || 'Export failed.');
      return;
    }
    const payload = result.payload;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vending-washer-config-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setExportMessage('Config exported. Raw secrets are excluded.');
  }

  return (
    <section className="dev-admin-panel">
      <div className="dev-admin-panel__header">
        <div>
          <p className="dev-admin-eyebrow">System status</p>
          <h2>Overview</h2>
        </div>
        <div className="dev-admin-actions">
          <button type="button" onClick={onReload}>Reload</button>
          <button type="button" className="dev-admin-primary" onClick={handleExport}>Export current config</button>
        </div>
      </div>

      <div className="dev-admin-warning">
        Export current config before risky settings or Advanced / Technical Mapping changes. For full rollback, also make a SQLite backup on the Pi.
      </div>

      <div className="dev-admin-status-grid">
        <StatusItem label="Backend reachable" value={status?.backend_reachable ? 'yes' : 'no'} tone={status?.backend_reachable ? 'success' : 'danger'} />
        <StatusItem label="Dev/admin enabled" value={status?.dev_admin_enabled ? 'yes' : 'no'} tone={status?.dev_admin_enabled ? 'warning' : 'danger'} />
        <StatusItem label="Provider" value={status?.app_mode?.provider_default || 'unknown'} />
        <StatusItem label="Reisa enabled" value={status?.app_mode?.provider_reisa_enabled ? 'yes' : 'no'} />
        <StatusItem label="Scanner port" value={status?.scanner?.serial_port || 'unknown'} />
        <StatusItem label="Scanner available" value={status?.scanner?.serial_available ? 'yes' : 'no'} tone={status?.scanner?.serial_available ? 'success' : 'warning'} />
        <StatusItem label="Current UI state" value={status?.runtime?.ui_state || 'unknown'} />
        <StatusItem label="Button box" value={status?.runtime?.button_box_enabled ? 'enabled' : 'disabled'} />
        <StatusItem label="Backend relay" value={status?.runtime?.backend_relay_enabled ? 'enabled' : 'disabled'} tone={status?.runtime?.backend_relay_enabled ? 'warning' : ''} />
        <StatusItem label="Telemetry" value={status?.runtime?.telemetry_enabled ? 'enabled' : 'disabled'} />
        <StatusItem label="Configured machines" value={status?.machines?.configured ?? 'unknown'} />
        <StatusItem label="Active in kiosk" value={status?.machines?.active_in_kiosk ?? 'unknown'} />
        <StatusItem label="Settings loaded" value={status?.settings_loaded_at || 'unknown'} />
      </div>
      {exportMessage ? <p className="dev-admin-save-message">{exportMessage}</p> : null}
    </section>
  );
}
