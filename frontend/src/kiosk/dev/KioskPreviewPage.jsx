import React, { useMemo, useState } from 'react';
import KioskRouter from '../KioskRouter.jsx';
import {
  defaultKioskPreviewScenarioId,
  getKioskPreviewScenarioById,
  kioskPreviewScenarios,
} from './kioskPreviewScenarios.js';

function getInitialScenarioId() {
  const params = new URLSearchParams(window.location.search);
  const scenarioFromUrl = params.get('scenario');

  if (!scenarioFromUrl) {
    return defaultKioskPreviewScenarioId;
  }

  return getKioskPreviewScenarioById(scenarioFromUrl).id;
}

export default function KioskPreviewPage() {
  const [scenarioId, setScenarioId] = useState(getInitialScenarioId);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const activeScenario = useMemo(() => getKioskPreviewScenarioById(scenarioId), [scenarioId]);

  function handleScenarioSelect(nextScenarioId) {
    setScenarioId(nextScenarioId);

    const url = new URL(window.location.href);
    url.searchParams.set('scenario', nextScenarioId);
    window.history.replaceState(null, '', url.toString());
  }

  return (
    <div className={`kiosk-preview-page ${!isSidebarOpen ? 'kiosk-preview-page--sidebar-closed' : ''}`}>
      <aside className="kiosk-preview-controls">
        <div className="kiosk-preview-controls__inner">
          <div className="kiosk-preview-controls__header">
            <h1 className="kiosk-preview-controls__title">Kiosk UI Preview</h1>
            <button className="kiosk-preview-toggle-btn" onClick={() => setIsSidebarOpen(false)} aria-label="Close sidebar">
              ✕
            </button>
          </div>
          <p className="kiosk-preview-controls__subtitle">Development-only state playground</p>
          <div className="kiosk-preview-controls__list" role="group" aria-label="Kiosk preview scenarios">
            {kioskPreviewScenarios.map((scenario) => (
              <button
                key={scenario.id}
                type="button"
                className={`kiosk-preview-controls__button ${
                  scenario.id === scenarioId ? 'is-active' : ''
                }`}
                onClick={() => handleScenarioSelect(scenario.id)}
              >
                {scenario.label}
              </button>
            ))}
          </div>
        </div>
      </aside>

      <div className="kiosk-preview-canvas">
        {!isSidebarOpen && (
          <button 
            className="kiosk-preview-toggle-btn kiosk-preview-toggle-btn--floating" 
            onClick={() => setIsSidebarOpen(true)}
          >
            <span aria-hidden="true">☰</span> Menu
          </button>
        )}
        <KioskRouter
          uiState={activeScenario.uiState}
          backendUnreachable={activeScenario.backendUnreachable}
        />
      </div>
    </div>
  );
}
