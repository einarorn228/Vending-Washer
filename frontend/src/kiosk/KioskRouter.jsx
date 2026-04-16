import React from 'react';
import ScanScreen from '../components/ScanScreen.jsx';
import MachineSelectScreen from '../components/MachineSelectScreen.jsx';
import ResultScreen from '../components/ResultScreen.jsx';

const connectionBannerStyle = {
  background: '#3d2914',
  color: '#ffcc80',
  padding: '0.6rem 1rem',
  textAlign: 'center',
  fontSize: '0.95rem',
};

export default function KioskRouter({ uiState, backendUnreachable }) {
  const banner = backendUnreachable ? (
    <div style={connectionBannerStyle}>
      Ekki náð í bakenda (API / net). Athugaðu að Flask keyri á port 5000, réttan{' '}
      <code style={{ color: '#ffe0b2' }}>VITE_API_KEY</code> eða{' '}
      <code style={{ color: '#ffe0b2' }}>localStorage API_KEY</code>, og að{' '}
      <code style={{ color: '#ffe0b2' }}>/api</code> sé proxy-að í Vite.
    </div>
  ) : null;

  switch (uiState.state) {
    case 'waiting_for_code':
      return (
        <>
          {banner}
          <ScanScreen message={uiState.message} />
        </>
      );
    case 'choose_machine':
      return (
        <>
          {banner}
          <MachineSelectScreen machines={uiState.machines} message={uiState.message} />
        </>
      );
    case 'machine_starting':
    case 'machine_in_use':
    case 'error':
      return (
        <>
          {banner}
          <ResultScreen message={uiState.message} />
        </>
      );
    default:
      return (
        <>
          {banner}
          <ResultScreen message={uiState.message || ''} />
        </>
      );
  }
}
