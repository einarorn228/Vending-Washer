import React from 'react';
import KioskRouter from './kiosk/KioskRouter.jsx';
import useUiStatePolling from './kiosk/hooks/useUiStatePolling.js';

export default function App() {
  const { uiState, backendUnreachable } = useUiStatePolling();

  return <KioskRouter uiState={uiState} backendUnreachable={backendUnreachable} />;
}
