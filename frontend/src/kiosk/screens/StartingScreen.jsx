import React from 'react';

function resolveMachineLabel(currentMachine, machines) {
  if (typeof currentMachine !== 'string' || !currentMachine.trim()) {
    return 'Selected machine';
  }

  const match = Array.isArray(machines)
    ? machines.find((machine) => machine?.id === currentMachine && typeof machine?.name === 'string')
    : null;

  return match?.name || currentMachine;
}

export default function StartingScreen({ message, currentMachine, machines, usesLeft }) {
  const machineLabel = resolveMachineLabel(currentMachine, machines);

  return (
    <section className="kiosk-screen kiosk-screen--starting">
      <div className="kiosk-hero kiosk-hero--compact kiosk-hero--confirmation">
        <p className="kiosk-hero__eyebrow">Start confirmed</p>
        <h2 className="kiosk-hero__title">Machine enabled</h2>
        <p className="kiosk-hero__message">
          {message || 'Load laundry, choose a program, and press Start on the machine.'}
        </p>
      </div>

      <div className="kiosk-detail-card kiosk-detail-card--confirmation kiosk-detail-card--machine">
        <p className="kiosk-detail-card__title">Machine</p>
        <p className="kiosk-machine-label">{machineLabel}</p>
        <p className="kiosk-detail-card__text">Uses left: {usesLeft ?? '—'}</p>
      </div>
    </section>
  );
}
