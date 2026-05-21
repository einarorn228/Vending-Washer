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
    'Selected machine';

  return {
    machineId: selectedMachine?.id || machineId || 'selected-machine',
    machineLabel,
    selectedMachine,
  };
}

export default function StartingScreen({ message, currentMachine, machines, usesLeft }) {
  const { machineId, machineLabel, selectedMachine } = resolveSelectedMachine(currentMachine, machines);
  const focusStatus = selectedMachine?.status === 'error' ? 'error' : 'reserved';
  const usesLeftMessage = usesLeft ?? null;
  const focusDetail = `Ready for program selection${usesLeftMessage !== null ? ` · Uses left: ${usesLeftMessage}` : ''}`;
  const fallbackMessage = `${machineLabel} is enabled. Choose your program and press Start on the machine.`;
  const focusMachine = {
    ...(selectedMachine || {}),
    id: selectedMachine?.id || machineId,
    name: selectedMachine?.name || machineLabel,
    status: focusStatus,
  };

  return (
    <section className="kiosk-screen kiosk-screen--starting kiosk-screen--machine-final">
      <div className="kiosk-stage-card kiosk-stage-card--hero kiosk-stage-card--confirmation kiosk-hero kiosk-hero--compact kiosk-hero--confirmation">
        <p className="kiosk-hero__eyebrow">Start confirmed</p>
        <h2 className="kiosk-hero__title">Machine enabled</h2>
        <p className="kiosk-hero__message">
          {message || fallbackMessage}
        </p>
      </div>

      <div className="kiosk-machine-focus">
        <MachineCard
          machine={focusMachine}
          isInteractive={false}
          variant="focus"
          detail={focusDetail}
        />
      </div>
    </section>
  );
}
