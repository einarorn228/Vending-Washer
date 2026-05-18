import React from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';
import ScanIcon from '../components/ScanIcon.jsx';

export default function HomeScreen({ machines }) {
  return (
    <section className="kiosk-screen kiosk-screen--home">
      <div className="kiosk-hero kiosk-hero--home">
        <div className="kiosk-scan-icon" aria-hidden="true">
          <div className="kiosk-scan-icon__wiggle-wrapper">
            <ScanIcon />
          </div>
          <span className="kiosk-scan-icon__laser" />
        </div>
        <h2 className="kiosk-hero__title">Scan your code</h2>
      </div>
      <MachineGrid machines={machines} isInteractive={false} variant="scan" />
    </section>
  );
}
