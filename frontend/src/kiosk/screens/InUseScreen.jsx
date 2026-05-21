import React from 'react';
import MachineCard from '../components/machine/MachineCard.jsx';

function resolveSelectedMachine(currentMachine, machines) {
  const machineId =
    typeof currentMachine === 'string'
      ? currentMachine.trim()
      : typeof currentMachine?.id === 'string'
        ? currentMachine.id
        : '';
  const machineNameFromCurrent =
    typeof currentMachine?.name === 'string' && currentMachine.name.trim()
      ? currentMachine.name
      : '';

  const matchedMachine = Array.isArray(machines)
    ? machines.find((machine) => machine?.id === machineId) ||
      machines.find((machine) => machine?.name === machineNameFromCurrent)
    : null;

  const selectedMachine = matchedMachine || (currentMachine && typeof currentMachine === 'object' ? currentMachine : null);
  const machineLabel =
    selectedMachine?.name ||
    machineNameFromCurrent ||
    matchedMachine?.id ||
    machineId ||
    'Current machine unavailable';

  return {
    machineId: selectedMachine?.id || machineId || 'in-use-machine',
    machineLabel,
    selectedMachine,
  };
}

function FinalInUseIcon() {
  return (
    <svg
      className="kiosk-final-status-card__icon-svg kiosk-final-status-card__icon-svg--active"
      viewBox="0 0 48 48"
      role="img"
      aria-label="Machine active status"
    >
      <circle cx="24" cy="24" r="15" className="kiosk-final-status-card__icon-stroke kiosk-final-status-card__icon-stroke--soft" />
      <path d="M17 24 H31" className="kiosk-final-status-card__icon-stroke" />
      <path d="M24 17 V31" className="kiosk-final-status-card__icon-stroke" />
      <circle cx="24" cy="24" r="4.2" className="kiosk-final-status-card__icon-fill" />
    </svg>
  );
}

export default function InUseScreen({ message, currentMachine, machines, usesLeft }) {
  const { machineId, machineLabel, selectedMachine } = resolveSelectedMachine(currentMachine, machines);
  const focusStatus = selectedMachine?.status === 'error' ? 'error' : 'busy';
  const usesLeftMessage = usesLeft ?? null;
  const focusDetail = `Program in progress${usesLeftMessage !== null ? ` · Uses left: ${usesLeftMessage}` : ''}`;
  const fallbackMessage = `${machineLabel} is running. No further action is needed—wait for the program to finish.`;
  const focusMachine = {
    ...(selectedMachine || {}),
    id: selectedMachine?.id || machineId,
    name: selectedMachine?.name || machineLabel,
    status: focusStatus,
  };

  return (
    <section className="kiosk-screen kiosk-screen--in-use kiosk-screen--machine-final">
      <div className="kiosk-stage-card kiosk-stage-card--hero kiosk-stage-card--confirmation kiosk-hero kiosk-hero--centered kiosk-hero--confirmation">
        <div className="kiosk-final-status-card kiosk-final-status-card--in-use kiosk-final-status-card--centered">
          <div className="kiosk-final-status-card__visual" aria-hidden="true">
            <FinalInUseIcon />
          </div>
          <div className="kiosk-final-status-card__body">
            <p className="kiosk-hero__eyebrow">In progress</p>
            <h2 className="kiosk-hero__title">Machine running</h2>
            <p className="kiosk-hero__message">
              {message || fallbackMessage}
            </p>
          </div>
        </div>
      </div>

      <div className="kiosk-machine-focus">
        <MachineCard
          machine={focusMachine}
          isInteractive={false}
          variant="focus"
          detail={focusDetail}
        >
          <div className="kiosk-final-status-card__meta">
            <div className="kiosk-final-status-card__status-chip">
              <p className="kiosk-final-status-card__countdown-label">Program status</p>
              <p className="kiosk-final-status-card__countdown-value">In progress</p>
              <p className="kiosk-final-status-card__status-subtle">No further action is needed.</p>
            </div>
            <p className="kiosk-final-status-card__helper">
              Wait for the selected program to finish.
            </p>
          </div>
        </MachineCard>
      </div>
    </section>
  );
}
