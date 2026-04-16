import React from 'react';
import ConnectionBanner from './components/chrome/ConnectionBanner.jsx';
import KioskHeader from './components/chrome/KioskHeader.jsx';
import KioskFooter from './components/chrome/KioskFooter.jsx';
import KioskProgressSteps from './components/chrome/KioskProgressSteps.jsx';
import './styles/kiosk.css';

export default function KioskAppShell({ backendUnreachable, currentState, children }) {
  const isWaitingForCode = currentState === 'waiting_for_code';

  return (
    <div className={`kiosk-shell ${isWaitingForCode ? 'kiosk-shell--scan-focus' : ''}`}>
      <ConnectionBanner visible={backendUnreachable} />
      {!isWaitingForCode ? <KioskHeader /> : null}
      <div className="kiosk-shell__topbar">
        <KioskProgressSteps currentState={currentState} />
      </div>
      <main className="kiosk-shell__content">{children}</main>
      {!isWaitingForCode ? <KioskFooter /> : null}
    </div>
  );
}
