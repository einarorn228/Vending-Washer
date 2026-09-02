import { useEffect, useRef, useState } from 'react';
import { pollState } from '../../api/backend.js';
import { adaptUiState } from '../adapters/uiStateAdapter.js';

const INITIAL_UI_STATE = {
  state: 'waiting_for_code',
  message: 'Scan your code to start',
};

export const DEFAULT_POLL_INTERVAL_MS = 1000;
const MIN_POLL_INTERVAL_MS = 250;
const MAX_POLL_INTERVAL_MS = 10000;

function normalizePollInterval(rawInterval) {
  const value = Number(rawInterval);
  if (!Number.isFinite(value)) return DEFAULT_POLL_INTERVAL_MS;
  if (value < MIN_POLL_INTERVAL_MS || value > MAX_POLL_INTERVAL_MS) {
    return DEFAULT_POLL_INTERVAL_MS;
  }
  return value;
}

export default function useUiStatePolling() {
  const [uiState, setUiState] = useState(INITIAL_UI_STATE);
  const [backendUnreachable, setBackendUnreachable] = useState(false);
  // The backend owns the cadence (kiosk_poll_interval_ms), so the interval is
  // re-armed whenever that value changes rather than being fixed at mount.
  const [pollIntervalMs, setPollIntervalMs] = useState(DEFAULT_POLL_INTERVAL_MS);
  const pollIntervalRef = useRef(DEFAULT_POLL_INTERVAL_MS);

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await pollState();
      const adaptedState = adaptUiState(data);

      if (adaptedState) {
        setBackendUnreachable(false);
        setUiState(adaptedState);

        const nextInterval = normalizePollInterval(adaptedState.poll_interval_ms);
        if (nextInterval !== pollIntervalRef.current) {
          pollIntervalRef.current = nextInterval;
          setPollIntervalMs(nextInterval);
        }
      } else {
        setBackendUnreachable(true);
      }
    }, pollIntervalMs);

    return () => clearInterval(interval);
  }, [pollIntervalMs]);

  return {
    uiState,
    backendUnreachable,
  };
}
