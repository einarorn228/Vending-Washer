import React from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';

export default function HomeScreen({ machines }) {
  return (
    <section className="kiosk-screen kiosk-screen--home">
      <div className="kiosk-hero kiosk-hero--home">
        <div className="kiosk-scan-icon" aria-hidden="true">
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--finder-tl" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--finder-tr" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--finder-bl" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--dot-a" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--dot-b" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--dot-c" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--line-h" />
          <span className="kiosk-scan-icon__module kiosk-scan-icon__module--line-v" />
        </div>
        <h2 className="kiosk-hero__title">Scan your code</h2>
      </div>
      <MachineGrid machines={machines} isInteractive={false} variant="scan" />
    </section>
  );
}
