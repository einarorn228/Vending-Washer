import React from 'react';
import ScanScreen from '../components/ScanScreen.jsx';
import MachineSelectScreen from '../components/MachineSelectScreen.jsx';
import ResultScreen from '../components/ResultScreen.jsx';
import KioskAppShell from './KioskAppShell.jsx';

export default function KioskRouter({ uiState, backendUnreachable }) {
  let content;

  switch (uiState.state) {
    case 'waiting_for_code':
      content = <ScanScreen message={uiState.message} />;
      break;
    case 'choose_machine':
      content = <MachineSelectScreen machines={uiState.machines} message={uiState.message} />;
      break;
    case 'machine_starting':
    case 'machine_in_use':
    case 'error':
      content = <ResultScreen message={uiState.message} />;
      break;
    default:
      content = <ResultScreen message={uiState.message || ''} />;
      break;
  }

  return <KioskAppShell backendUnreachable={backendUnreachable}>{content}</KioskAppShell>;
}
