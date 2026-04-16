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

function resolveMachineType(machineName) {
  return machineName.toLowerCase().includes('dryer') ? 'dryer' : 'washer';
}

export default function MachineCard({ machine, isInteractive, onSelect, variant = 'default' }) {
  const machineName = machine?.name || machine?.id || 'Machine';
  const status = normalizeMachineStatus(machine);
  const isAvailable = status === 'available';
  const isCardInteractive = isInteractive && isAvailable;
  const machineType = resolveMachineType(machineName);
  const isScanVariant = variant === 'scan';

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
      className={`machine-card machine-card--${variant} machine-card--${status} ${isCardInteractive ? 'machine-card--interactive' : 'machine-card--readonly'}`}
      onClick={handleCardActivate}
      onKeyDown={handleCardKeyDown}
      role={isCardInteractive ? 'button' : undefined}
      tabIndex={isCardInteractive ? 0 : undefined}
      aria-label={isCardInteractive ? `Select ${machineName}` : undefined}
      aria-disabled={isInteractive && !isAvailable ? true : undefined}
    >
      {isScanVariant ? (
        <div className="machine-card__icon-wrap" aria-hidden="true">
          <span className={`machine-card__icon machine-card__icon--${machineType}`} />
        </div>
      ) : null}

      <div className="machine-card__content">
        {!isScanVariant ? <p className="machine-card__label">Machine</p> : null}
        <h3 className="machine-card__title">{machineName}</h3>
        <MachineStatusBadge status={status} />
        {!isScanVariant ? <p className="machine-card__hint">{resolveHint(status, isInteractive)}</p> : null}
      </div>
    </article>
  );
}
