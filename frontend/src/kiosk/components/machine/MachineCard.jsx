import React from 'react';
import MachineStatusBadge from './MachineStatusBadge.jsx';
import MachineIcon from './MachineIcon.jsx';
import { normalizeMachineStatus } from './normalizeMachineStatus.js';
import AutoFitText from '../common/AutoFitText.jsx';

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

function resolveMachineType(machine) {
  if (machine?.type === 'washer' || machine?.type === 'dryer') {
    return machine.type;
  }

  const machineName = machine?.name || '';
  return machineName.toLowerCase().includes('dryer') ? 'dryer' : 'washer';
}

export default function MachineCard({ machine, isInteractive, onSelect, variant = 'default' }) {
  const machineName = machine?.name || machine?.id || 'Machine';
  const status = normalizeMachineStatus(machine);
  const isAvailable = status === 'available';
  const isCardInteractive = isInteractive && isAvailable;
  const machineType = resolveMachineType(machine);
  const isScanVariant = variant === 'scan';
  const isFocusVariant = variant === 'focus';
  const isDefaultVariant = variant === 'default';
  const showsMachineIcon = isScanVariant || isDefaultVariant || isFocusVariant;

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
      {showsMachineIcon ? (
        <div className="machine-card__icon-wrap" aria-hidden="true">
          <MachineIcon type={machineType} className="machine-card__icon" />
        </div>
      ) : null}

      <div className="machine-card__content">
        {!isScanVariant ? <p className="machine-card__label">Machine</p> : null}
        <AutoFitText as="h3" className="machine-card__title" minScale={0.5}>{machineName}</AutoFitText>
        <MachineStatusBadge status={status} />
        {!isScanVariant && !isFocusVariant ? (
          <p className="machine-card__hint">{resolveHint(status, isInteractive)}</p>
        ) : null}
      </div>
    </article>
  );
}
