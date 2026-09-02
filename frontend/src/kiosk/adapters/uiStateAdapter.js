export function adaptUiState(rawUiState) {
  if (!rawUiState || typeof rawUiState !== 'object') {
    return null;
  }

  return {
    ...rawUiState,
    state: typeof rawUiState.state === 'string' ? rawUiState.state : '',
    message: typeof rawUiState.message === 'string' ? rawUiState.message : '',
    input_mode: typeof rawUiState.input_mode === 'string' ? rawUiState.input_mode : undefined,
    button_box_enabled: typeof rawUiState.button_box_enabled === 'boolean' ? rawUiState.button_box_enabled : undefined,
    reservation_minutes: Number.isFinite(Number(rawUiState.reservation_minutes))
      ? Number(rawUiState.reservation_minutes)
      : undefined,
    poll_interval_ms: Number.isFinite(Number(rawUiState.poll_interval_ms))
      ? Number(rawUiState.poll_interval_ms)
      : undefined,
  };
}
