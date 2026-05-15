const baseMachines = [
  { id: 'wm-01', name: 'Washer 1', status: 'available' },
  { id: 'wm-02', name: 'Washer 2', status: 'busy' },
  { id: 'wm-03', name: 'Washer 3', status: 'error' },
  { id: 'dr-01', name: 'Dryer 1', status: 'available' },
  { id: 'dr-02', name: 'Dryer 2', status: 'reserved' },
  { id: 'dr-03', name: 'Dryer 3', status: 'available' },
];

const busyMachines = baseMachines.map((machine) => ({
  ...machine,
  status: machine.status === 'error' ? 'error' : 'busy',
}));

export const kioskPreviewScenarios = [
  {
    id: 'scan-screen',
    label: 'Scan screen',
    backendUnreachable: false,
    uiState: {
      state: 'waiting_for_code',
      message: 'Scan your QR code to begin.',
      machines: baseMachines,
      uses_left: null,
      current_machine: null,
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
  {
    id: 'valid-scan-select-machine',
    label: 'Valid scan / select machine',
    backendUnreachable: false,
    uiState: {
      state: 'choose_machine',
      message: 'Code accepted. Choose any available machine.',
      machines: baseMachines,
      uses_left: 2,
      current_machine: null,
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },

  {
    id: 'touch-only-select-machine',
    label: 'Touch only / no button box',
    backendUnreachable: false,
    uiState: {
      state: 'choose_machine',
      message: 'Code accepted. Touch is active; button box is disabled.',
      machines: baseMachines,
      uses_left: 2,
      current_machine: null,
      input_mode: 'hardware_buttons',
      button_box_enabled: false,
    },
  },
  {
    id: 'touch-and-button-box-select-machine',
    label: 'Touch + button box enabled',
    backendUnreachable: false,
    uiState: {
      state: 'choose_machine',
      message: 'Code accepted. Touch is active; button box is also enabled.',
      machines: baseMachines,
      uses_left: 2,
      current_machine: null,
      input_mode: 'hardware_buttons',
      button_box_enabled: true,
    },
  },
  {
    id: 'invalid-code-error',
    label: 'Invalid code / error',
    backendUnreachable: false,
    uiState: {
      state: 'error',
      message: 'Invalid or expired code. Please try again.',
      machines: baseMachines,
      uses_left: null,
      current_machine: null,
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
  {
    id: 'machine-selected-starting',
    label: 'Machine selected / starting',
    backendUnreachable: false,
    uiState: {
      state: 'machine_starting',
      message: 'Washer 1 is now enabled. Press Start on the machine.',
      machines: baseMachines,
      uses_left: 1,
      current_machine: 'wm-01',
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
  {
    id: 'machine-in-use',
    label: 'Machine in use',
    backendUnreachable: false,
    uiState: {
      state: 'machine_in_use',
      message: 'Your wash cycle is in progress.',
      machines: baseMachines,
      uses_left: 1,
      current_machine: 'wm-01',
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
  {
    id: 'all-machines-busy',
    label: 'All machines busy',
    backendUnreachable: false,
    uiState: {
      state: 'choose_machine',
      message: 'All machines are currently busy. Please wait for one to become available.',
      machines: busyMachines,
      uses_left: 2,
      current_machine: null,
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
  {
    id: 'thank-you-activated',
    label: 'Thank you / activated',
    backendUnreachable: false,
    uiState: {
      state: 'machine_starting',
      message: 'Thank you! Your machine is activated.',
      machines: baseMachines,
      uses_left: 0,
      current_machine: 'dr-01',
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
  {
    id: 'backend-unreachable',
    label: 'Backend unreachable',
    backendUnreachable: true,
    uiState: {
      state: 'waiting_for_code',
      message: 'Backend is unreachable.',
      machines: baseMachines,
      uses_left: null,
      current_machine: null,
      input_mode: 'touch',
      button_box_enabled: false,
    },
  },
];

export const defaultKioskPreviewScenarioId = kioskPreviewScenarios[0].id;

export function getKioskPreviewScenarioById(id) {
  return kioskPreviewScenarios.find((scenario) => scenario.id === id) || kioskPreviewScenarios[0];
}
