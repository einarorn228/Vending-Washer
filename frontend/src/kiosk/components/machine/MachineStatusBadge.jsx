import React from 'react';

export default function MachineStatusBadge({ available }) {
  const isAvailable = Boolean(available);
  const label = isAvailable ? 'AVAILABLE' : 'IN USE';

  return (
    <span
      className={`machine-status-badge ${isAvailable ? 'machine-status-badge--available' : 'machine-status-badge--busy'}`}
      aria-label={`Machine status: ${isAvailable ? 'Available' : 'In use'}`}
    >
      {label}
    </span>
  );
}
