import React from 'react';
import KioskAppShell from './KioskAppShell.jsx';
import { adaptInputMode } from './adapters/inputModeAdapter.js';
import createInteractionPolicy from './interaction/createInteractionPolicy.js';
import HomeScreen from './screens/HomeScreen.jsx';
import SelectMachineScreen from './screens/SelectMachineScreen.jsx';
import StartingScreen from './screens/StartingScreen.jsx';
import InUseScreen from './screens/InUseScreen.jsx';
import ErrorScreen from './screens/ErrorScreen.jsx';

export default function KioskRouter({ uiState, backendUnreachable }) {
  const { inputMode, isFallback } = adaptInputMode(uiState);
  const interactionPolicy = createInteractionPolicy({ inputMode, isFallback });

  const screenProps = {
    interactionPolicy,
    inputMode,
    currentMachine: uiState?.current_machine,
    usesLeft: uiState?.uses_left,
    machines: uiState?.machines,
  };

  let content;

  switch (uiState.state) {
    case 'waiting_for_code':
      content = <HomeScreen message={uiState.message} {...screenProps} />;
      break;
    case 'choose_machine':
      content = (
        <SelectMachineScreen
          machines={uiState.machines}
          message={uiState.message}
          {...screenProps}
        />
      );
      break;
    case 'machine_starting':
      content = <StartingScreen message={uiState.message} {...screenProps} />;
      break;
    case 'machine_in_use':
      content = <InUseScreen message={uiState.message} {...screenProps} />;
      break;
    case 'error':
      content = <ErrorScreen message={uiState.message} {...screenProps} />;
      break;
    default:
      content = <ErrorScreen message={uiState.message || ''} {...screenProps} />;
      break;
  }

  return (
    <KioskAppShell backendUnreachable={backendUnreachable} currentState={uiState.state}>
      {content}
    </KioskAppShell>
  );
}
