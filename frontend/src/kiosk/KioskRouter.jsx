import React from 'react';
import ScanScreen from '../components/ScanScreen.jsx';
import MachineSelectScreen from '../components/MachineSelectScreen.jsx';
import ResultScreen from '../components/ResultScreen.jsx';
import KioskAppShell from './KioskAppShell.jsx';
import { adaptInputMode } from './adapters/inputModeAdapter.js';
import createInteractionPolicy from './interaction/createInteractionPolicy.js';

export default function KioskRouter({ uiState, backendUnreachable }) {
  const { inputMode, isFallback } = adaptInputMode(uiState);
  const interactionPolicy = createInteractionPolicy({ inputMode, isFallback });

  const screenProps = {
    interactionPolicy,
    inputMode,
  };

  let content;

  switch (uiState.state) {
    case 'waiting_for_code':
      content = <ScanScreen message={uiState.message} {...screenProps} />;
      break;
    case 'choose_machine':
      content = (
        <MachineSelectScreen
          machines={uiState.machines}
          message={uiState.message}
          {...screenProps}
        />
      );
      break;
    case 'machine_starting':
    case 'machine_in_use':
    case 'error':
      content = <ResultScreen message={uiState.message} {...screenProps} />;
      break;
    default:
      content = <ResultScreen message={uiState.message || ''} {...screenProps} />;
      break;
  }

  return <KioskAppShell backendUnreachable={backendUnreachable}>{content}</KioskAppShell>;
}
