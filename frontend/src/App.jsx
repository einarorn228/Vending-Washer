import React, { useState, useEffect } from 'react';
import ScanScreen from './components/ScanScreen.jsx';
import MachineSelectScreen from './components/MachineSelectScreen.jsx';
import ResultScreen from './components/ResultScreen.jsx';
import { pollState } from './api/backend.js';

export default function App() {
  const [uiState, setUiState] = useState({ state: 'waiting_for_code', message: 'Ready' });

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await pollState();
      if (data) setUiState(data);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  switch (uiState.state) {
    case 'waiting_for_code':
      return <ScanScreen message={uiState.message} />;
    case 'choose_machine':
      return (
        <MachineSelectScreen machines={uiState.machines} message={uiState.message} />
      );
    case 'machine_in_use':
    case 'error':
      return <ResultScreen message={uiState.message} />;
    default:
      return <ResultScreen message={uiState.message || ''} />;
  }
}
