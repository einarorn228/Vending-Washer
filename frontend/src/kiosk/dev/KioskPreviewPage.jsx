import React, { useMemo, useState } from 'react';
import KioskRouter from '../KioskRouter.jsx';
import MachineSettingsModal from './MachineSettingsModal.jsx';
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

function getScenarioMachines(scenario) {
  return scenario?.uiState?.machines || [];
}

export default function KioskPreviewPage() {
  const [scenarioId, setScenarioId] = useState(getInitialScenarioId);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const activeScenario = useMemo(() => getKioskPreviewScenarioById(scenarioId), [scenarioId]);
  const [previewMachines, setPreviewMachines] = useState(() => getScenarioMachines(activeScenario));

  const effectiveUiState = useMemo(() => {
    const scenarioUiState = activeScenario.uiState || {};
    const machines = previewMachines?.length ? previewMachines : getScenarioMachines(activeScenario);
    const nextUiState = {
      ...scenarioUiState,
      machines,
    };

    if (scenarioUiState.currentMachine || scenarioUiState.current_machine) {
      const existingCurrentMachine = scenarioUiState.currentMachine || scenarioUiState.current_machine;
      const machineById = machines.find((machine) => machine.id === existingCurrentMachine?.id);
      const fallbackMachine = machines.find((machine) => machine.status === 'available') || machines[0] || null;
      const nextCurrentMachine = machineById || fallbackMachine;

      nextUiState.currentMachine = nextCurrentMachine;
      nextUiState.current_machine = nextCurrentMachine;
    }

    return nextUiState;
  }, [activeScenario, previewMachines]);

  function handleScenarioSelect(nextScenarioId) {
    setScenarioId(nextScenarioId);

    const url = new URL(window.location.href);
    url.searchParams.set('scenario', nextScenarioId);
    window.history.replaceState(null, '', url.toString());
  }

  function handleMachineSettingsSave(nextMachines) {
    setPreviewMachines(nextMachines);
    setIsSettingsOpen(false);
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
          <button
            type="button"
            className="kiosk-preview-settings-button"
            onClick={() => setIsSettingsOpen(true)}
          >
            Machine Settings
          </button>
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
          uiState={effectiveUiState}
          backendUnreachable={activeScenario.backendUnreachable}
        />
      </div>

      <MachineSettingsModal
        isOpen={isSettingsOpen}
        initialMachines={previewMachines}
        onClose={() => setIsSettingsOpen(false)}
        onSave={handleMachineSettingsSave}
      />
    </div>
  );
}
