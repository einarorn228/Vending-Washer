export function adaptUiState(rawUiState) {
  if (!rawUiState || typeof rawUiState !== 'object') {
    return null;
  }

  return {
    ...rawUiState,
    state: typeof rawUiState.state === 'string' ? rawUiState.state : '',
    message: typeof rawUiState.message === 'string' ? rawUiState.message : '',
  };
}
