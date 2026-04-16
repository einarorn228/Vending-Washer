import React from 'react';

function resolveMachineLabel(currentMachine, machines) {
  if (typeof currentMachine !== 'string' || !currentMachine.trim()) {
    return 'Current machine unavailable';
  }

  const match = Array.isArray(machines)
    ? machines.find((machine) => machine?.id === currentMachine && typeof machine?.name === 'string')
    : null;

  return match?.name || currentMachine;
}

export default function InUseScreen({ message, currentMachine, machines, usesLeft }) {
  return (
    <section className="kiosk-screen kiosk-screen--in-use">
      <div className="kiosk-hero kiosk-hero--compact kiosk-hero--confirmation">
        <p className="kiosk-hero__eyebrow">In progress</p>
        <h2 className="kiosk-hero__title">Machine running</h2>
        <p className="kiosk-hero__message">{message || 'Your machine is currently running.'}</p>
      </div>

      <div className="kiosk-detail-card kiosk-detail-card--confirmation kiosk-detail-card--machine">
        <p className="kiosk-detail-card__title">Machine</p>
        <p className="kiosk-machine-label">{resolveMachineLabel(currentMachine, machines)}</p>
        <p className="kiosk-detail-card__text">Uses left: {usesLeft ?? '—'}</p>
      </div>
    </section>
  );
}
