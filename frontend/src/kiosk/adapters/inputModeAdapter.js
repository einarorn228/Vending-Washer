const TOUCH_MODE = 'touch';
const HARDWARE_BUTTONS_MODE = 'hardware_buttons';

function normalizeInputMode(rawInputMode) {
  if (typeof rawInputMode !== 'string') {
    return null;
  }

  const normalized = rawInputMode.trim().toLowerCase();

  if (normalized === TOUCH_MODE) {
    return TOUCH_MODE;
  }

  if (normalized === HARDWARE_BUTTONS_MODE) {
    return HARDWARE_BUTTONS_MODE;
  }

  return null;
}

export function adaptInputMode(rawUiState) {
  const configuredMode = normalizeInputMode(rawUiState?.input_mode);

  if (configuredMode) {
    return {
      inputMode: configuredMode,
      isFallback: false,
    };
  }

  return {
    inputMode: HARDWARE_BUTTONS_MODE,
    isFallback: true,
  };
}

export { TOUCH_MODE, HARDWARE_BUTTONS_MODE };
