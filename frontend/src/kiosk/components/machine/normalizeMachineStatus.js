const STATUS_ALIASES = {
  in_use: 'busy',
  occupied: 'busy',
  unavailable: 'busy',
};

const SUPPORTED_STATUSES = new Set(['available', 'busy', 'reserved', 'error']);

export function normalizeMachineStatus(input) {
  const rawStatus =
    typeof input === 'string'
      ? input
      : typeof input?.status === 'string'
        ? input.status
        : input?.available
          ? 'available'
          : 'busy';

  const normalized = rawStatus.trim().toLowerCase();
  const mapped = STATUS_ALIASES[normalized] || normalized;

  if (SUPPORTED_STATUSES.has(mapped)) {
    return mapped;
  }

  return 'busy';
}
