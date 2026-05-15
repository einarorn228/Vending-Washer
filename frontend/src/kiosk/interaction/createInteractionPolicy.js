import { HARDWARE_BUTTONS_MODE, TOUCH_MODE } from '../adapters/inputModeAdapter.js';

export default function createInteractionPolicy({ inputMode, isFallback }) {
  const isTouchMode = inputMode === TOUCH_MODE;
  const isHardwareButtonsMode = inputMode === HARDWARE_BUTTONS_MODE;

  return {
    inputMode,
    isFallback,
    isTouchMode,
    isHardwareButtonsMode,
    // Touch machine selection is always enabled when the screen state allows it.
    // Legacy inputMode is preserved for compatibility and display only.
    allowTouchPrimaryActions: isTouchMode,
    allowTouchMachineSelect: true,
    allowTouchSecondaryActions: false,
  };
}
