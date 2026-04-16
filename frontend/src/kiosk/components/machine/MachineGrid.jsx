import React from 'react';
import MachineCard from './MachineCard.jsx';

export default function MachineGrid({ machines, isInteractive, onSelect }) {
  if (!machines?.length) {
    return (
      <section className="machine-grid machine-grid--empty" aria-live="polite">
        <p>No machines are currently reported by the backend.</p>
      </section>
    );
  }

  return (
    <section className="machine-grid" aria-live="polite">
      {machines.map((machine) => (
        <MachineCard
          key={machine.id}
          machine={machine}
          isInteractive={isInteractive}
          onSelect={onSelect}
        />
      ))}
    </section>
  );
}
