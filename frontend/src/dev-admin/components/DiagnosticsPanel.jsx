import React, { useEffect, useRef, useState } from 'react';
import { getDevAdminDiagnostics, getDevAdminTelemetry } from '../api.js';
import ContextualHelpLink from '../help/ContextualHelpLink.jsx';
import { formatHistogramEntry } from '../metricsFormat.js';

const TELEMETRY_POLL_MS = 1000;
const DIAGNOSTICS_POLL_MS = 10000;
// An unreachable or rejecting backend must not turn this tab into a request storm
// on the Pi, so each poll loop backs off after consecutive failures.
const MAX_BACKOFF_MS = 30000;
// Roughly two minutes of history at a 1s poll — enough to see a machine spin up.
const HISTORY_LENGTH = 120;

// Band names come from telemetry._classify_band: high / low / mid.
const BAND_LABELS = {
  high: 'at or above ON threshold',
  low: 'at or below OFF threshold',
  mid: 'between thresholds',
};

const BAND_TONES = {
  high: 'tone-success',
  low: '',
  mid: 'tone-warning',
};

function formatValue(value) {
  if (value === null || value === undefined) return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return numeric.toFixed(2);
}

function formatSeconds(value) {
  if (value === null || value === undefined) return '—';
  return `${Number(value).toFixed(1)}s`;
}

/**
 * Reading history plotted against the machine's own on/off thresholds — the two
 * lines you are actually trying to place when tuning.
 */
function ReadingChart({ history, onThreshold, offThreshold }) {
  const width = 320;
  const height = 72;

  if (!history.length) {
    return <div className="dev-admin-chart dev-admin-chart--empty">waiting for readings…</div>;
  }

  const numericValues = history.filter((value) => Number.isFinite(value));
  const candidates = [...numericValues, Number(onThreshold), Number(offThreshold)].filter((value) =>
    Number.isFinite(value),
  );
  const max = Math.max(...candidates);
  const min = Math.min(...candidates, 0);
  const span = max - min || 1;

  const toY = (value) => height - ((value - min) / span) * height;
  const step = history.length > 1 ? width / (history.length - 1) : width;

  const points = history
    .map((value, index) => (Number.isFinite(value) ? `${index * step},${toY(value)}` : null))
    .filter(Boolean)
    .join(' ');

  return (
    <svg className="dev-admin-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Recent readings against thresholds">
      {Number.isFinite(Number(onThreshold)) ? (
        <line x1="0" x2={width} y1={toY(Number(onThreshold))} y2={toY(Number(onThreshold))} className="dev-admin-chart__on" />
      ) : null}
      {Number.isFinite(Number(offThreshold)) ? (
        <line x1="0" x2={width} y1={toY(Number(offThreshold))} y2={toY(Number(offThreshold))} className="dev-admin-chart__off" />
      ) : null}
      <polyline points={points} className="dev-admin-chart__line" />
    </svg>
  );
}

export default function DiagnosticsPanel({ apiKey }) {
  const [telemetry, setTelemetry] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [error, setError] = useState('');
  const [view, setView] = useState('live');
  // Kept in a ref so appending a sample does not re-render the whole tab twice.
  const historyRef = useRef({});
  const [historyTick, setHistoryTick] = useState(0);

  // Only the live view needs 1 Hz telemetry; polling it behind the scan log,
  // audit and metrics views was pure Pi load with nothing rendering it.
  useEffect(() => {
    if (view !== 'live') return undefined;

    let cancelled = false;
    let timer = null;
    let failures = 0;

    async function fetchTelemetry() {
      const result = await getDevAdminTelemetry(apiKey);
      if (cancelled) return;

      if (!result.ok || !result.payload?.success) {
        failures += 1;
        setError(result.payload?.message || 'Could not read telemetry.');
      } else {
        failures = 0;
        setError('');
        setTelemetry(result.payload);
        (result.payload.machines || []).forEach((machine) => {
          const series = historyRef.current[machine.id] || [];
          series.push(machine.last_value);
          if (series.length > HISTORY_LENGTH) series.shift();
          historyRef.current[machine.id] = series;
        });
        setHistoryTick((tick) => tick + 1);
      }

      // Self-scheduling rather than setInterval: a slow response cannot stack
      // requests, and repeated failures widen the gap instead of hammering.
      const delay = failures
        ? Math.min(TELEMETRY_POLL_MS * 2 ** failures, MAX_BACKOFF_MS)
        : TELEMETRY_POLL_MS;
      timer = setTimeout(fetchTelemetry, delay);
    }

    fetchTelemetry();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [apiKey, view]);

  // Scan log, audit trail and metrics all come from /diagnostics; the live view
  // does not render any of them.
  useEffect(() => {
    if (view === 'live') return undefined;

    let cancelled = false;
    let timer = null;
    let failures = 0;

    async function fetchDiagnostics() {
      const result = await getDevAdminDiagnostics(apiKey);
      if (cancelled) return;

      if (result.ok && result.payload?.success) {
        failures = 0;
        setDiagnostics(result.payload);
      } else {
        failures += 1;
      }

      const delay = failures
        ? Math.min(DIAGNOSTICS_POLL_MS * 2 ** failures, MAX_BACKOFF_MS)
        : DIAGNOSTICS_POLL_MS;
      timer = setTimeout(fetchDiagnostics, delay);
    }

    fetchDiagnostics();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [apiKey, view]);

  const machines = telemetry?.machines || [];

  return (
    <div style={{ display: 'grid', gap: '1.25rem' }}>
      <section className="dev-admin-panel">
        <div className="dev-admin-panel__header">
          <div>
            <p className="dev-admin-eyebrow">Live</p>
            <h2>Diagnostics</h2>
          </div>
          <div className="dev-admin-actions">
            <button type="button" className={view === 'live' ? 'dev-admin-primary' : ''} onClick={() => setView('live')}>
              Live readings
            </button>
            <button type="button" className={view === 'scans' ? 'dev-admin-primary' : ''} onClick={() => setView('scans')}>
              Scan log
            </button>
            <button type="button" className={view === 'audit' ? 'dev-admin-primary' : ''} onClick={() => setView('audit')}>
              Change history
            </button>
            <button type="button" className={view === 'metrics' ? 'dev-admin-primary' : ''} onClick={() => setView('metrics')}>
              Metrics
            </button>
          </div>
        </div>

        {error ? <div className="dev-admin-form-error">{error}</div> : null}
        {telemetry && !telemetry.telemetry_enabled ? (
          <div className="dev-admin-warning dev-admin-warning--danger">
            Telemetry polling is turned off, so these readings will not update and every machine
            reports as available. Enable “Telemetry polling enabled” in Settings to tune thresholds.
          </div>
        ) : null}
      </section>

      {view === 'live' ? (
        <section className="dev-admin-panel">
          <h3>Live machine readings<ContextualHelpLink guideId="tune-thresholds" label="Help: tune thresholds" /></h3>
          <p style={{ color: 'var(--kiosk-muted)', margin: '0 0 1rem' }}>
            Run a machine and watch the value. The ON threshold must sit below the running value,
            the OFF threshold above the idle value. “Above for” tells you whether the confirm window
            is long enough.
          </p>
          {machines.length === 0 ? (
            <p className="dev-admin-save-message">No machines are loaded in the telemetry runtime.</p>
          ) : null}
          <div className="dev-admin-diagnostics-grid">
            {machines.map((machine) => (
              <article key={machine.id} className="dev-admin-group-card" data-history-tick={historyTick}>
                <div className="dev-admin-diff__head">
                  <strong>{machine.name}</strong>
                  <span className={`dev-admin-badge ${machine.is_enabled ? '' : 'dev-admin-badge--restart'}`}>
                    {machine.is_enabled ? 'active' : 'inactive'}
                  </span>
                  <span className="dev-admin-badge">{machine.device?.metric_source || 'no metric'}</span>
                </div>

                <div className="dev-admin-reading">
                  <span className="dev-admin-reading__value">{formatValue(machine.last_value)}</span>
                  <span className={`dev-admin-reading__band ${BAND_TONES[machine.band] || ''}`}>
                    {BAND_LABELS[machine.band] || 'no reading'}
                  </span>
                </div>

                <ReadingChart
                  history={historyRef.current[machine.id] || []}
                  onThreshold={machine.config?.on_threshold}
                  offThreshold={machine.config?.off_threshold}
                />

                <div className="dev-admin-readonly-grid">
                  <span>Run state</span><strong>{machine.run_state}</strong>
                  <span>Available</span><strong>{machine.available ? 'yes' : 'no'}</strong>
                  <span>Pending start</span><strong>{machine.pending_start ? 'yes' : 'no'}</strong>
                  <span>Last read</span><strong>{formatSeconds(machine.seconds_since_read)} ago</strong>
                  <span>Above for</span><strong>{formatSeconds(machine.seconds_above)}</strong>
                  <span>Below for</span><strong>{formatSeconds(machine.seconds_below)}</strong>
                  <span>ON threshold</span><strong>{machine.config?.on_threshold ?? '—'}</strong>
                  <span>OFF threshold</span><strong>{machine.config?.off_threshold ?? '—'}</strong>
                  <span>ON confirm</span><strong>{machine.config?.on_confirm_ms ?? '—'} ms</strong>
                  <span>OFF confirm</span><strong>{machine.config?.off_confirm_ms ?? '—'} ms</strong>
                  <span>Poll interval</span><strong>{machine.config?.poll_interval_ms ?? '—'} ms</strong>
                  <span>Device</span><strong>{machine.device?.ip || '—'}</strong>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {view === 'scans' ? (
        <section className="dev-admin-panel">
          <h3>Recent scans</h3>
          <div className="dev-admin-table-scroll">
            <table className="dev-admin-table">
              <thead>
                <tr><th>Time</th><th>Code</th><th>Order</th><th>Result</th><th>Details</th></tr>
              </thead>
              <tbody>
                {(diagnostics?.scan_logs || []).map((log) => (
                  <tr key={log.id}>
                    <td>{log.timestamp || '—'}</td>
                    <td><code>{log.code}</code></td>
                    <td>{log.order_id || '—'}</td>
                    <td>{log.result}</td>
                    <td>{log.details || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!diagnostics?.scan_logs?.length ? <p className="dev-admin-save-message">No scans recorded yet.</p> : null}
        </section>
      ) : null}

      {view === 'audit' ? (
        <section className="dev-admin-panel">
          <h3>Configuration change history</h3>
          <p style={{ color: 'var(--kiosk-muted)', margin: '0 0 1rem' }}>
            Every settings and machine change made through this panel. Use it to tie a change in
            kiosk behaviour back to the configuration change that caused it. Secrets are recorded
            by presence only, never by value.
          </p>
          <div className="dev-admin-table-scroll">
            <table className="dev-admin-table">
              <thead>
                <tr><th>Time</th><th>What</th><th>Field</th><th>From</th><th>To</th><th>Flags</th></tr>
              </thead>
              <tbody>
                {(diagnostics?.audit_log || []).map((entry) => (
                  <tr key={entry.id} className={entry.is_high_risk ? 'is-high-risk' : ''}>
                    <td>{entry.created_at || '—'}</td>
                    <td>{entry.entity_key}</td>
                    <td>{entry.field}</td>
                    <td>{entry.old_value ?? '—'}</td>
                    <td>{entry.new_value ?? '—'}</td>
                    <td>
                      {entry.is_high_risk ? <span className="dev-admin-badge dev-admin-badge--high">high risk</span> : null}
                      {entry.restart_required ? <span className="dev-admin-badge dev-admin-badge--restart">restart</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!diagnostics?.audit_log?.length ? <p className="dev-admin-save-message">No configuration changes recorded yet.</p> : null}
        </section>
      ) : null}

      {view === 'metrics' ? (
        <section className="dev-admin-panel">
          <h3>Runtime metrics</h3>
          <div className="dev-admin-table-scroll">
            <table className="dev-admin-table">
              <thead>
                <tr><th>Metric</th><th>Labels</th><th>Value</th></tr>
              </thead>
              <tbody>
                {[...(diagnostics?.metrics?.counters || []), ...(diagnostics?.metrics?.gauges || [])].map((entry, index) => (
                  <tr key={`${entry.name}-${index}`}>
                    <td>{entry.name}</td>
                    <td>{Object.entries(entry.labels || {}).map(([k, v]) => `${k}=${v}`).join(', ') || '—'}</td>
                    <td>{entry.value}</td>
                  </tr>
                ))}
                {(diagnostics?.metrics?.histograms || []).map((entry, index) => (
                  <tr key={`histo-${entry.name}-${index}`}>
                    <td>{entry.name}</td>
                    <td>{Object.entries(entry.labels || {}).map(([k, v]) => `${k}=${v}`).join(', ') || '—'}</td>
                    <td>{formatHistogramEntry(entry)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}
