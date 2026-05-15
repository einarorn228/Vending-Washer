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

  const activeScenario = useMemo(() => getKioskPreviewScenarioById(scenarioId), [scenarioId]);

  function handleScenarioSelect(nextScenarioId) {
    setScenarioId(nextScenarioId);

    const url = new URL(window.location.href);
    url.searchParams.set('scenario', nextScenarioId);
    window.history.replaceState(null, '', url.toString());
  }

  return (
    <div className="kiosk-preview-page">
      <aside className="kiosk-preview-controls">
        <h1 className="kiosk-preview-controls__title">Kiosk UI Preview</h1>
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
      </aside>

      <div className="kiosk-preview-canvas">
        <KioskRouter
          uiState={activeScenario.uiState}
          backendUnreachable={activeScenario.backendUnreachable}
        />
      </div>
    </div>
  );
}
