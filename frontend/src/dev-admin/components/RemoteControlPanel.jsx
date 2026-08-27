import React, { useEffect, useRef, useState } from 'react';
import { getKioskState, remoteReset, remoteScan, remoteTouchSelect } from '../api.js';

const STATE_LABELS = {
  waiting_for_code: 'Waiting for scan',
  choose_machine: 'Choose machine',
  machine_starting: 'Starting machine',
  machine_in_use: 'Machine in use',
  error: 'Error',
};

const STATE_TONES = {
  waiting_for_code: '',
  choose_machine: 'tone-warning',
  machine_starting: 'tone-warning',
  machine_in_use: 'tone-success',
  error: 'tone-danger',
};

export default function RemoteControlPanel({ apiKey }) {
  const [kioskState, setKioskState] = useState(null);
  const [pollingError, setPollingError] = useState('');

  const [scanCode, setScanCode] = useState('');
  const [scanLoading, setScanLoading] = useState(false);
  const [scanMessage, setScanMessage] = useState('');
  const [scanError, setScanError] = useState('');

  const [selectLoading, setSelectLoading] = useState('');
  const [selectMessage, setSelectMessage] = useState('');
  const [selectError, setSelectError] = useState('');

  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState('');

  const pollRef = useRef(null);

  async function fetchKioskState() {
    const result = await getKioskState(apiKey);
    if (result.ok && result.payload?.success) {
      setKioskState(result.payload.kiosk_state);
      setPollingError('');
    } else {
      setPollingError(result.payload?.message || 'Could not reach backend.');
    }
  }

  useEffect(() => {
    fetchKioskState();
    pollRef.current = setInterval(fetchKioskState, 2000);
    return () => clearInterval(pollRef.current);
  }, [apiKey]);

  async function handleScan(e) {
    e.preventDefault();
    setScanLoading(true);
    setScanMessage('');
    setScanError('');
    const result = await remoteScan(apiKey, scanCode.trim());
    setScanLoading(false);
    if (result.ok && result.payload?.success) {
      setScanMessage(result.payload.message || 'Scan accepted.');
      setScanCode('');
    } else {
      setScanError(result.payload?.message || 'Scan failed.');
    }
  }

  async function handleTouchSelect(machineId) {
    setSelectLoading(machineId);
    setSelectMessage('');
    setSelectError('');
    const result = await remoteTouchSelect(apiKey, machineId);
    setSelectLoading('');
    if (result.ok && result.payload?.success) {
      setSelectMessage(result.payload.message || 'Machine selected.');
    } else {
      setSelectError(result.payload?.message || 'Selection failed.');
    }
  }

  async function handleReset() {
    setResetLoading(true);
    setResetMessage('');
    const result = await remoteReset(apiKey);
    setResetLoading(false);
    if (result.ok && result.payload?.success) {
      setResetMessage('Kiosk reset to ready state.');
    }
  }

  const state = kioskState?.state || '—';
  const machines = kioskState?.machines || [];
  const inChooseMachine = state === 'choose_machine';

  return (
    <div style={{ display: 'grid', gap: '1.25rem' }}>
      <div className="dev-admin-panel">
        <div className="dev-admin-panel__header">
          <div>
            <p className="dev-admin-eyebrow">Live</p>
            <h2>Remote Control</h2>
          </div>
          <div className="dev-admin-actions">
            <button type="button" onClick={fetchKioskState} className="dev-admin-secondary">
              Refresh
            </button>
          </div>
        </div>

        {pollingError && <div className="dev-admin-form-error" style={{ marginTop: '0.75rem' }}>{pollingError}</div>}

        <div className="dev-admin-status-grid" style={{ marginTop: '1rem' }}>
          <div className="dev-admin-status-item">
            <span>State</span>
            <strong className={STATE_TONES[state] || ''}>{STATE_LABELS[state] || state}</strong>
          </div>
          <div className="dev-admin-status-item">
            <span>Message</span>
            <strong>{kioskState?.message || '—'}</strong>
          </div>
          <div className="dev-admin-status-item">
            <span>Current Machine</span>
            <strong>{kioskState?.current_machine || '—'}</strong>
          </div>
          <div className="dev-admin-status-item">
            <span>Uses Left</span>
            <strong>{kioskState?.uses_left ?? '—'}</strong>
          </div>
        </div>
      </div>

      <div className="dev-admin-panel">
        <h3 style={{ marginBottom: '0.5rem' }}>Inject Scan</h3>
        <p style={{ color: 'var(--kiosk-muted)', margin: '0 0 1rem' }}>
          Simulate a QR code scan at the kiosk. Kiosk must be in "waiting for scan" state.
        </p>
        <form onSubmit={handleScan} style={{ display: 'grid', gap: '0.9rem' }}>
          <label style={{ display: 'grid', gap: '0.4rem', color: '#d9e6fa', fontWeight: 700 }}>
            Access Code
            <input
              type="text"
              value={scanCode}
              onChange={e => setScanCode(e.target.value)}
              placeholder="Enter access code…"
              autoComplete="off"
            />
          </label>
          {scanMessage && <div className="dev-admin-save-message">{scanMessage}</div>}
          {scanError && <div className="dev-admin-form-error">{scanError}</div>}
          <div>
            <button
              type="submit"
              className="dev-admin-primary"
              disabled={scanLoading || !scanCode.trim()}
            >
              {scanLoading ? 'Injecting…' : 'Inject Scan'}
            </button>
          </div>
        </form>
      </div>

      {inChooseMachine && machines.length > 0 && (
        <div className="dev-admin-panel">
          <h3 style={{ marginBottom: '0.5rem' }}>Select Machine</h3>
          <p style={{ color: 'var(--kiosk-muted)', margin: '0 0 1rem' }}>
            A scan is armed. Select a machine to start it.
          </p>
          {selectMessage && <div className="dev-admin-save-message" style={{ marginBottom: '0.75rem' }}>{selectMessage}</div>}
          {selectError && <div className="dev-admin-form-error" style={{ marginBottom: '0.75rem' }}>{selectError}</div>}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
            {machines.map(m => (
              <button
                key={m.id}
                type="button"
                className={m.available ? 'dev-admin-primary' : ''}
                disabled={!m.available || selectLoading === m.id}
                onClick={() => handleTouchSelect(m.id)}
              >
                {selectLoading === m.id ? 'Starting…' : (m.name || m.id)}
                {!m.available && ' (busy)'}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="dev-admin-panel">
        <h3 style={{ marginBottom: '0.5rem' }}>Reset Kiosk</h3>
        <p style={{ color: 'var(--kiosk-muted)', margin: '0 0 0.75rem' }}>
          Force the kiosk UI back to "waiting for scan", cancelling any active session or selection.
        </p>
        <div className="dev-admin-warning dev-admin-warning--danger" style={{ marginBottom: '0.75rem' }}>
          This will interrupt any in-progress scan or machine selection.
        </div>
        {resetMessage && <div className="dev-admin-save-message" style={{ marginBottom: '0.75rem' }}>{resetMessage}</div>}
        <button
          type="button"
          className="dev-admin-danger"
          disabled={resetLoading}
          onClick={handleReset}
        >
          {resetLoading ? 'Resetting…' : 'Reset to Ready'}
        </button>
      </div>
    </div>
  );
}
