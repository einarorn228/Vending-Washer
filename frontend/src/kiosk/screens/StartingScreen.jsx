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

function formatCountdown(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function resolveCountdown(selectionSecondsLeft, selectionExpiresAt) {
  if (Number.isFinite(Number(selectionSecondsLeft))) {
    return Number(selectionSecondsLeft);
  }

  if (typeof selectionExpiresAt === 'string') {
    const expiresAtMs = Date.parse(selectionExpiresAt);
    if (Number.isFinite(expiresAtMs)) {
      return Math.max(0, Math.floor((expiresAtMs - Date.now()) / 1000));
    }
  }

  return null;
}

function FinalStartingIcon() {
  return (
    <svg
      className="kiosk-final-status-card__icon-svg"
      viewBox="0 0 48 48"
      role="img"
      aria-label="Start window timer"
    >
      <circle cx="24" cy="26" r="14" className="kiosk-final-status-card__icon-stroke" />
      <path d="M24 26 L24 18" className="kiosk-final-status-card__icon-stroke" />
      <path d="M24 26 L31 30" className="kiosk-final-status-card__icon-stroke" />
      <path d="M20 8 H28" className="kiosk-final-status-card__icon-stroke" />
      <path d="M17 11 L20 14" className="kiosk-final-status-card__icon-stroke kiosk-final-status-card__icon-stroke--soft" />
      <path d="M31 11 L28 14" className="kiosk-final-status-card__icon-stroke kiosk-final-status-card__icon-stroke--soft" />
    </svg>
  );
}

export default function StartingScreen({
  message,
  currentMachine,
  machines,
  usesLeft,
  selectionSecondsLeft,
  selectionExpiresAt,
}) {
  const { machineId, machineLabel, selectedMachine } = resolveSelectedMachine(currentMachine, machines);
  const focusStatus = selectedMachine?.status === 'error' ? 'error' : 'reserved';
  const usesLeftMessage = usesLeft ?? null;
  const focusDetail = `Ready for program selection${usesLeftMessage !== null ? ` · Uses left: ${usesLeftMessage}` : ''}`;
  const fallbackMessage = `${machineLabel} is enabled. Choose your program and press Start on the machine.`;
  const countdownSeconds = resolveCountdown(selectionSecondsLeft, selectionExpiresAt);
  const hasCountdown = countdownSeconds !== null;
  const startWindowLabel = hasCountdown ? 'Start window remaining' : 'Start window';
  const startWindowValue = hasCountdown ? formatCountdown(countdownSeconds) : '10 min';
  const startWindowHint = hasCountdown
    ? 'No use is taken if time runs out.'
    : 'Scan again if the start window expires.';
  const focusMachine = {
    ...(selectedMachine || {}),
    id: selectedMachine?.id || machineId,
    name: selectedMachine?.name || machineLabel,
    status: focusStatus,
  };

  return (
    <section className="kiosk-screen kiosk-screen--starting kiosk-screen--machine-final">
      <div className="kiosk-stage-card kiosk-stage-card--hero kiosk-stage-card--confirmation kiosk-hero kiosk-hero--compact kiosk-hero--confirmation">
        <div className="kiosk-final-status-card kiosk-final-status-card--starting">
          <div className="kiosk-final-status-card__visual" aria-hidden="true">
            <FinalStartingIcon />
          </div>
          <div className="kiosk-final-status-card__body">
            <p className="kiosk-hero__eyebrow">Start confirmed</p>
            <h2 className="kiosk-hero__title">Machine enabled</h2>
            <p className="kiosk-hero__message">
              {message || fallbackMessage}
            </p>
          </div>
          <div className="kiosk-final-status-card__meta">
            <div className="kiosk-final-status-card__status-chip">
              <p className="kiosk-final-status-card__countdown-label">{startWindowLabel}</p>
              <p className="kiosk-final-status-card__countdown-value">{startWindowValue}</p>
              <p className="kiosk-final-status-card__status-subtle">{startWindowHint}</p>
            </div>
            <p className="kiosk-final-status-card__helper">
              You have 10 minutes to choose a program and press Start. If time runs out, no use is taken and you can scan again.
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
        />
      </div>
    </section>
  );
}
