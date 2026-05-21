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

export default function InUseScreen({ message, currentMachine, machines, usesLeft }) {
  const { machineId, machineLabel, selectedMachine } = resolveSelectedMachine(currentMachine, machines);
  const focusStatus = selectedMachine?.status === 'error' ? 'error' : 'busy';
  const usesLeftMessage = usesLeft ?? null;
  const focusDetail = `Machine running${usesLeftMessage !== null ? ` · Uses left: ${usesLeftMessage}` : ''}`;
  const fallbackMessage = `${machineLabel} is now running. No further action is needed—wait for the selected program to finish.`;
  const focusMachine = {
    ...(selectedMachine || {}),
    id: selectedMachine?.id || machineId,
    name: selectedMachine?.name || machineLabel,
    status: focusStatus,
  };

  return (
    <section className="kiosk-screen kiosk-screen--in-use kiosk-screen--machine-final">
      <div className="kiosk-stage-card kiosk-stage-card--hero kiosk-stage-card--confirmation kiosk-hero kiosk-hero--compact kiosk-hero--confirmation">
        <p className="kiosk-hero__eyebrow">In progress</p>
        <h2 className="kiosk-hero__title">Machine running</h2>
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
