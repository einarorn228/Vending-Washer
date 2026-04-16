import { HARDWARE_BUTTONS_MODE, TOUCH_MODE } from '../adapters/inputModeAdapter.js';

export default function createInteractionPolicy({ inputMode, isFallback }) {
  const isTouchMode = inputMode === TOUCH_MODE;
  const isHardwareButtonsMode = inputMode === HARDWARE_BUTTONS_MODE;

  return {
    inputMode,
    isFallback,
    isTouchMode,
    isHardwareButtonsMode,
    // Centralized defaults: keep kiosk safe/read-only unless explicitly in touch mode.
    allowTouchPrimaryActions: isTouchMode,
    allowTouchMachineSelect: isTouchMode,
    allowTouchSecondaryActions: false,
  };
}
