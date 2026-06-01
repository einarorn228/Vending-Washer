import React from 'react';
import KioskRouter from './kiosk/KioskRouter.jsx';
import useUiStatePolling from './kiosk/hooks/useUiStatePolling.js';
import KioskPreviewPage from './kiosk/dev/KioskPreviewPage.jsx';
import DevAdminPage from './dev-admin/DevAdminPage.jsx';

const DEV_KIOSK_PREVIEW_PATH = '/dev/kiosk-preview';
const DEV_ADMIN_PATH = '/dev/admin';

function RealKioskApp() {
  const { uiState, backendUnreachable } = useUiStatePolling();

  return <KioskRouter uiState={uiState} backendUnreachable={backendUnreachable} />;
}

export default function App() {
  const isDevAdminRoute = window.location.pathname.startsWith(DEV_ADMIN_PATH);
  const isDevPreviewRoute =
    import.meta.env.DEV && window.location.pathname.startsWith(DEV_KIOSK_PREVIEW_PATH);

  if (isDevAdminRoute) {
    return <DevAdminPage />;
  }

  if (isDevPreviewRoute) {
    return <KioskPreviewPage />;
  }

  return <RealKioskApp />;
}
