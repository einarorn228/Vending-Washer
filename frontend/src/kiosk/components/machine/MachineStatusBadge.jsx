import React from 'react';
import { normalizeMachineStatus } from './normalizeMachineStatus.js';

export default function MachineStatusBadge({ status }) {
  const normalizedStatus = normalizeMachineStatus(status);

  const labelByStatus = {
    available: 'Available',
    busy: 'In use',
    reserved: 'Reserved',
    error: 'Error',
  };

  const a11yByStatus = {
    available: 'Available',
    busy: 'In use',
    reserved: 'Reserved',
    error: 'Error',
  };

  return (
    <span
      className={`machine-status-badge machine-status-badge--${normalizedStatus}`}
      aria-label={`Machine status: ${a11yByStatus[normalizedStatus]}`}
    >
      {labelByStatus[normalizedStatus]}
    </span>
  );
}
