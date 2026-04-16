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

export default function StartingScreen({ message, currentMachine, machines, usesLeft, inputMode }) {
  const machineLabel = resolveMachineLabel(currentMachine, machines);

  return (
    <section className="kiosk-screen kiosk-screen--starting">
      <div className="kiosk-hero kiosk-hero--compact">
        <p className="kiosk-hero__eyebrow">Starting</p>
        <h2 className="kiosk-hero__title">Almost ready</h2>
        <p className="kiosk-hero__message">{message || 'Your machine is being started.'}</p>
      </div>

      <div className="kiosk-detail-card kiosk-detail-card--confirmation">
        <p className="kiosk-detail-card__title">Machine confirmed</p>
        <p className="kiosk-machine-label">{machineLabel}</p>
        <p className="kiosk-detail-card__text">Uses left: {usesLeft ?? '—'}</p>
        <p className="kiosk-detail-card__text kiosk-detail-card__text--muted">
          {inputMode === 'touch'
            ? 'Please wait while the backend confirms machine start.'
            : 'Please wait while hardware and backend complete machine start.'}
        </p>
      </div>
    </section>
  );
}
