import React, { useState } from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';
import ScanIcon from '../components/ScanIcon.jsx';
import { simulateScanCode } from '../../api/backend.js';

export default function HomeScreen({ machines }) {
  const [testCode, setTestCode] = useState('fb5c794b-9d5c-466f-9e14-335ccf8066a7');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSimulate = async () => {
    if (!testCode.trim()) {
      setErrorMsg('Vinsamlegast sláðu inn kóða');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await simulateScanCode(testCode);
      if (!res || !res.success) {
        setErrorMsg(res?.message || 'Skönnun mistókst. Kóðinn gæti verið ógildur.');
      }
    } catch (err) {
      setErrorMsg('Villa kom upp við að tengjast bakenda.');
    } finally {
      setLoading(false);
    }
  };

  const isDevPreview = typeof window !== 'undefined' && (
    window.location.pathname.includes('/dev') || 
    window.location.href.includes('scenario') ||
    window.location.href.includes('preview')
  );

  return (
    <section className="kiosk-screen kiosk-screen--home" style={{ position: 'relative' }}>
      <div className="kiosk-hero kiosk-hero--home" style={{ position: 'relative' }}>
        {isDevPreview && (
          <div
            className="kiosk-dev-simulator-compact"
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.75rem',
              borderRadius: '12px',
              background: 'rgba(15, 23, 42, 0.75)',
              border: '1px solid rgba(112, 200, 255, 0.25)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
              maxWidth: '340px',
            }}
          >
            <input
              type="text"
              value={testCode}
              onChange={(e) => setTestCode(e.target.value)}
              placeholder="Kóði..."
              title="Prófunarkóði"
              style={{
                width: '130px',
                padding: '0.35rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                background: 'rgba(255, 255, 255, 0.05)',
                color: '#fff',
                fontSize: '0.8rem',
                outline: 'none',
                fontFamily: 'monospace',
              }}
            />
            <button
              onClick={handleSimulate}
              disabled={loading}
              style={{
                padding: '0.35rem 0.8rem',
                borderRadius: '6px',
                border: 'none',
                background: loading ? 'rgba(255, 255, 255, 0.15)' : 'linear-gradient(135deg, var(--kiosk-accent) 0%, #3b82f6 100%)',
                color: '#fff',
                fontWeight: '700',
                fontSize: '0.8rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 2px 8px rgba(112, 200, 255, 0.2)',
              }}
            >
              {loading ? '...' : 'Simulate'}
            </button>
            {errorMsg && (
              <span 
                title={errorMsg}
                style={{ 
                  fontSize: '0.75rem', 
                  color: 'var(--kiosk-danger)', 
                  fontWeight: '600',
                  cursor: 'help'
                }}
              >
                ⚠️
              </span>
            )}
          </div>
        )}

        <div className="kiosk-scan-icon" aria-hidden="true">
          <div className="kiosk-scan-icon__wiggle-wrapper">
            <ScanIcon />
          </div>
          <span className="kiosk-scan-icon__laser" />
        </div>
        <h2 className="kiosk-hero__title">Scan your code</h2>
      </div>
      <MachineGrid machines={machines} isInteractive={false} variant="scan" />
    </section>
  );
}

