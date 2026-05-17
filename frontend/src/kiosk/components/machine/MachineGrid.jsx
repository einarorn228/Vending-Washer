import React from 'react';
import MachineCard from './MachineCard.jsx';

function clampMachineCount(machineCount) {
  return Math.max(1, Math.min(8, machineCount));
}

export default function MachineGrid({ machines, isInteractive, onSelect, variant = 'default' }) {
  if (!machines?.length) {
    return (
      <section className="machine-grid machine-grid--empty" aria-live="polite">
        <p>No machines are currently reported by the backend.</p>
      </section>
    );
  }

  const machineCount = machines.length;
  const clampedCount = clampMachineCount(machineCount);

  return (
    <section
      className={`machine-grid machine-grid--${variant} machine-grid--count-${clampedCount}`}
      data-machine-count={clampedCount}
      aria-live="polite"
    >
      {machines.map((machine) => (
        <MachineCard
          key={machine.id}
          machine={machine}
          isInteractive={isInteractive}
          onSelect={onSelect}
          variant={variant}
        />
      ))}
    </section>
  );
}
