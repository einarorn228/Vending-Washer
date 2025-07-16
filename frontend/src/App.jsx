import React, { useState, useEffect } from 'react';
import ScanScreen from './components/ScanScreen.jsx';
import MachineSelectScreen from './components/MachineSelectScreen.jsx';
import ResultScreen from './components/ResultScreen.jsx';
import { pollState, scanCode, startMachine } from './api/backend.js';

export default function App() {
  const [uiState, setUiState] = useState({ state: 'waiting_for_code' });
  const [code, setCode] = useState('');

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await pollState();
      if (data) setUiState(data);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async (value) => {
    setCode(value);
    const resp = await scanCode(value);
    if (resp) setUiState(resp);
  };

  const handleStart = async (machineId) => {
    const resp = await startMachine(code, machineId);
    if (resp) setUiState(resp);
  };

  switch (uiState.state) {
    case 'choose_machine':
      return (
        <MachineSelectScreen machines={uiState.machines} onSelect={handleStart} />
      );
    case 'machine_in_use':
    case 'error':
    default:
      return (
        <ResultScreen message={uiState.message} />
      );
    case 'waiting_for_code':
      return <ScanScreen onScan={handleScan} />;
  }
}
