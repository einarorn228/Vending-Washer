import React from 'react';
import ConnectionBanner from './components/chrome/ConnectionBanner.jsx';
import KioskProgressSteps from './components/chrome/KioskProgressSteps.jsx';
import './styles/kiosk.css';

export default function KioskAppShell({ backendUnreachable, currentState, children }) {
  return (
    <div className="kiosk-shell">
      <div className="kiosk-beta-watermark">BETA Testing</div>
      <ConnectionBanner visible={backendUnreachable} />
      <div className="kiosk-shell__topbar">
        <KioskProgressSteps currentState={currentState} />
      </div>
      <main className="kiosk-shell__content">{children}</main>
    </div>
  );
}
