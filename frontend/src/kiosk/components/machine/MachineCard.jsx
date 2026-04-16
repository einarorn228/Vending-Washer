import React from 'react';
import MachineStatusBadge from './MachineStatusBadge.jsx';

export default function MachineCard({ machine, isInteractive, onSelect }) {
  const machineName = machine?.name || machine?.id || 'Machine';
  const isAvailable = Boolean(machine?.available);
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
      className={`machine-card machine-card--${isAvailable ? 'available' : 'busy'} ${isCardInteractive ? 'machine-card--interactive' : 'machine-card--readonly'}`}
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
        <p className="machine-card__id">{machine?.id || 'Unknown ID'}</p>
      </div>

      <div className="machine-card__actions">
        <MachineStatusBadge available={isAvailable} />
        <p className="machine-card__hint">
          {isInteractive
            ? isAvailable
              ? 'Tap to select'
              : 'Currently unavailable'
            : 'Use hardware buttons'}
        </p>
      </div>
    </article>
  );
}
