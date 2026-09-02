import React, { useState } from 'react';

// Changes that can take the kiosk or the operator offline, or move real hardware.
// Each of these must be acknowledged individually, not just as part of a bulk save.
const ACKNOWLEDGEMENT_REQUIRED = {
  backend_relay_enabled: {
    appliesWhen: (value) => value === true,
    warning: 'Turning this on means selecting a machine sends real power to real hardware. Confirm the relay wiring is correct first.',
  },
  cors_allowed_origins: {
    appliesWhen: () => true,
    warning: 'A wrong value here can stop the kiosk screen and this admin page from reaching the backend at all.',
  },
  provider_default: {
    appliesWhen: () => true,
    warning: 'This changes how every scanned code is validated.',
  },
  provider_reisa_enabled: {
    appliesWhen: () => true,
    warning: 'This gates whether the external Reisa system is used for validation.',
  },
  api_key: {
    appliesWhen: () => true,
    warning: 'Rotating the API key immediately cuts off every kiosk still using the old key.',
  },
  reisa_bearer_token: {
    appliesWhen: () => true,
    warning: 'An incorrect token means Reisa rejects every request.',
  },
};

function displayValue(value) {
  if (value === true) return 'Enabled';
  if (value === false) return 'Disabled';
  if (value === null || value === undefined || value === '') return '(empty)';
  if (Array.isArray(value)) return value.join(', ') || '(empty)';
  return String(value);
}

export function requiresAcknowledgement(key, nextValue) {
  const rule = ACKNOWLEDGEMENT_REQUIRED[key];
  return Boolean(rule && rule.appliesWhen(nextValue));
}

const RISK_ORDER = { high: 0, medium: 1, low: 2 };

export default function ChangeReviewModal({ changes, onCancel, onConfirm, saving }) {
  const [acknowledged, setAcknowledged] = useState({});

  const ordered = [...changes].sort(
    (a, b) => (RISK_ORDER[a.risk] ?? 3) - (RISK_ORDER[b.risk] ?? 3),
  );
  const gated = ordered.filter((change) => requiresAcknowledgement(change.key, change.next));
  const allAcknowledged = gated.every((change) => acknowledged[change.key]);
  const restartKeys = ordered.filter((change) => change.restartRequired);

  return (
    <div className="dev-admin-modal-overlay" role="presentation">
      <div className="dev-admin-modal dev-admin-modal--review" role="dialog" aria-modal="true" aria-labelledby="change-review-title">
        <h3 id="change-review-title">Review {ordered.length} change{ordered.length === 1 ? '' : 's'}</h3>
        <p>Check each value before it is written to the running system.</p>

        <ul className="dev-admin-diff-list">
          {ordered.map((change) => {
            const gate = ACKNOWLEDGEMENT_REQUIRED[change.key];
            const needsAck = requiresAcknowledgement(change.key, change.next);
            return (
              <li key={change.key} className={`dev-admin-diff ${needsAck ? 'is-gated' : ''}`}>
                <div className="dev-admin-diff__head">
                  <strong>{change.label}</strong>
                  <span className={`dev-admin-badge dev-admin-badge--${change.risk || 'low'}`}>risk: {change.risk || 'low'}</span>
                  {change.restartRequired ? <span className="dev-admin-badge dev-admin-badge--restart">restart required</span> : null}
                </div>
                <div className="dev-admin-diff__values">
                  <span className="dev-admin-diff__old">{displayValue(change.previous)}</span>
                  <span className="dev-admin-diff__arrow" aria-label="changes to">→</span>
                  <span className="dev-admin-diff__new">{displayValue(change.next)}</span>
                </div>
                {needsAck ? (
                  <label className="dev-admin-confirm">
                    <input
                      type="checkbox"
                      checked={Boolean(acknowledged[change.key])}
                      onChange={(event) =>
                        setAcknowledged((current) => ({ ...current, [change.key]: event.target.checked }))
                      }
                    />
                    {gate.warning}
                  </label>
                ) : null}
              </li>
            );
          })}
        </ul>

        {restartKeys.length ? (
          <div className="dev-admin-warning">
            {restartKeys.length} of these only take effect after the backend is restarted. You will be reminded after saving.
          </div>
        ) : null}

        <footer className="dev-admin-drawer__actions">
          <button type="button" onClick={onCancel} disabled={saving}>Cancel</button>
          <button
            type="button"
            className="dev-admin-primary"
            disabled={!allAcknowledged || saving}
            onClick={onConfirm}
          >
            {saving ? 'Saving…' : 'Apply changes'}
          </button>
        </footer>
      </div>
    </div>
  );
}
