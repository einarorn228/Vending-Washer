import React from 'react';
import ConnectionBanner from './components/chrome/ConnectionBanner.jsx';
import KioskHeader from './components/chrome/KioskHeader.jsx';
import KioskFooter from './components/chrome/KioskFooter.jsx';
import KioskProgressSteps from './components/chrome/KioskProgressSteps.jsx';
import './styles/kiosk.css';

export default function KioskAppShell({ backendUnreachable, currentState, children }) {
  return (
    <div className="kiosk-shell">
      <ConnectionBanner visible={backendUnreachable} />
      <KioskHeader />
      <div className="kiosk-shell__topbar">
        <KioskProgressSteps currentState={currentState} />
      </div>
      <main className="kiosk-shell__content">{children}</main>
      <KioskFooter />
    </div>
  );
}
