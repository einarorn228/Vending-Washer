import React from 'react';
import KioskRouter from './kiosk/KioskRouter.jsx';
import useUiStatePolling from './kiosk/hooks/useUiStatePolling.js';
import KioskPreviewPage from './kiosk/dev/KioskPreviewPage.jsx';

const DEV_KIOSK_PREVIEW_PATH = '/dev/kiosk-preview';

function RealKioskApp() {
  const { uiState, backendUnreachable } = useUiStatePolling();

  return <KioskRouter uiState={uiState} backendUnreachable={backendUnreachable} />;
}

export default function App() {
  const isDevPreviewRoute =
    import.meta.env.DEV && window.location.pathname.startsWith(DEV_KIOSK_PREVIEW_PATH);

  if (isDevPreviewRoute) {
    return <KioskPreviewPage />;
  }

  return <RealKioskApp />;
}
