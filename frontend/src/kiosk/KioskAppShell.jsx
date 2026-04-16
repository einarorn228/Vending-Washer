import React from 'react';
import ConnectionBanner from './components/chrome/ConnectionBanner.jsx';
import KioskHeader from './components/chrome/KioskHeader.jsx';
import KioskFooter from './components/chrome/KioskFooter.jsx';
import './styles/kiosk.css';

export default function KioskAppShell({ backendUnreachable, children }) {
  return (
    <div className="kiosk-shell">
      <ConnectionBanner visible={backendUnreachable} />
      <KioskHeader />
      <main className="kiosk-shell__content">{children}</main>
      <KioskFooter />
    </div>
  );
}
