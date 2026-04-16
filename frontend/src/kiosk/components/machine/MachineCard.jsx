import React from 'react';
import MachineStatusBadge from './MachineStatusBadge.jsx';
import { normalizeMachineStatus } from './normalizeMachineStatus.js';

function resolveHint(status, isInteractive) {
  if (!isInteractive) {
    return 'Use hardware buttons';
  }

  switch (status) {
    case 'available':
      return 'Tap to select';
    case 'reserved':
      return 'Reserved';
    case 'error':
      return 'Needs service';
    default:
      return 'Currently unavailable';
  }
}

export default function MachineCard({ machine, isInteractive, onSelect }) {
  const machineName = machine?.name || machine?.id || 'Machine';
  const status = normalizeMachineStatus(machine);
  const isAvailable = status === 'available';
  const isCardInteractive = isInteractive && isAvailable;

  function handleCardActivate() {
    if (isCardInteractive) {
      onSelect?.(machine);
    }
  }

  function handleCardKeyDown(event) {
    if (!isCardInteractive) {
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect?.(machine);
    }
  }

  return (
    <article
      className={`machine-card machine-card--${status} ${isCardInteractive ? 'machine-card--interactive' : 'machine-card--readonly'}`}
      onClick={handleCardActivate}
      onKeyDown={handleCardKeyDown}
      role={isCardInteractive ? 'button' : undefined}
      tabIndex={isCardInteractive ? 0 : undefined}
      aria-label={isCardInteractive ? `Select ${machineName}` : undefined}
      aria-disabled={isInteractive && !isAvailable ? true : undefined}
    >
      <div className="machine-card__content">
        <p className="machine-card__label">Machine</p>
        <h3 className="machine-card__title">{machineName}</h3>
        <p className="machine-card__id">ID: {machine?.id || 'Unknown'}</p>
      </div>

      <div className="machine-card__actions">
        <MachineStatusBadge status={status} />
        <p className="machine-card__hint">{resolveHint(status, isInteractive)}</p>
      </div>
    </article>
  );
}
