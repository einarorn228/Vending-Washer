import React from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';

export default function HomeScreen({ machines }) {
  return (
    <section className="kiosk-screen kiosk-screen--home">
      <div className="kiosk-hero kiosk-hero--home">
        <div className="kiosk-scan-icon" aria-hidden="true">
          <span className="kiosk-scan-icon__corner kiosk-scan-icon__corner--tl" />
          <span className="kiosk-scan-icon__corner kiosk-scan-icon__corner--tr" />
          <span className="kiosk-scan-icon__corner kiosk-scan-icon__corner--bl" />
          <span className="kiosk-scan-icon__corner kiosk-scan-icon__corner--br" />
          <span className="kiosk-scan-icon__dot kiosk-scan-icon__dot--1" />
          <span className="kiosk-scan-icon__dot kiosk-scan-icon__dot--2" />
          <span className="kiosk-scan-icon__dot kiosk-scan-icon__dot--3" />
          <span className="kiosk-scan-icon__dot kiosk-scan-icon__dot--4" />
        </div>
        <h2 className="kiosk-hero__title">Scan your code</h2>
      </div>
      <MachineGrid machines={machines} isInteractive={false} variant="scan" />
    </section>
  );
}
