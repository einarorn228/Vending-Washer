import { useEffect, useState } from 'react';
import { pollState } from '../../api/backend.js';
import { adaptUiState } from '../adapters/uiStateAdapter.js';

const INITIAL_UI_STATE = {
  state: 'waiting_for_code',
  message: 'Scan your code to start',
};

export default function useUiStatePolling() {
  const [uiState, setUiState] = useState(INITIAL_UI_STATE);
  const [backendUnreachable, setBackendUnreachable] = useState(false);

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await pollState();
      const adaptedState = adaptUiState(data);

      if (adaptedState) {
        setBackendUnreachable(false);
        setUiState(adaptedState);
      } else {
        setBackendUnreachable(true);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return {
    uiState,
    backendUnreachable,
  };
}
