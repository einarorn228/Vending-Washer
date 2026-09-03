import React from 'react';
import KioskRouter from './kiosk/KioskRouter.jsx';
import useUiStatePolling from './kiosk/hooks/useUiStatePolling.js';
import KioskPreviewPage from './kiosk/dev/KioskPreviewPage.jsx';
import DevAdminPage from './dev-admin/DevAdminPage.jsx';
import PublicHelpPage from './public-help/PublicHelpPage.jsx';

const DEV_KIOSK_PREVIEW_PATH = '/dev/kiosk-preview';
const DEV_ADMIN_PATH = '/dev/admin';
const PUBLIC_HELP_PATH = '/help';

function RealKioskApp() {
  const { uiState, backendUnreachable } = useUiStatePolling();

  return <KioskRouter uiState={uiState} backendUnreachable={backendUnreachable} />;
}

export default function App() {
  const isDevAdminRoute = window.location.pathname.startsWith(DEV_ADMIN_PATH);
  const isDevPreviewRoute =
    import.meta.env.DEV && window.location.pathname.startsWith(DEV_KIOSK_PREVIEW_PATH);
  const isPublicHelpRoute = window.location.pathname.startsWith(PUBLIC_HELP_PATH);

  if (isPublicHelpRoute) {
    return <PublicHelpPage />;
  }

  if (isDevAdminRoute) {
    return <DevAdminPage />;
  }

  if (isDevPreviewRoute) {
    return <KioskPreviewPage />;
  }

  return <RealKioskApp />;
}
