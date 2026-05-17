import React, { useEffect, useState } from 'react';

const MACHINE_TYPES = ['washer', 'dryer'];
const MACHINE_STATUSES = ['available', 'busy', 'reserved', 'error'];

function createDefaultMachine(index) {
  const number = index + 1;
  const type = index % 2 === 0 ? 'washer' : 'dryer';
  const sequence = Math.floor(index / 2) + 1;
  const prefix = type === 'washer' ? 'Washer' : 'Dryer';

  return {
    id: `preview-machine-${number}`,
    name: `${prefix} ${sequence}`,
    type,
    status: 'available',
  };
}

function resizeDraftMachines(machines, nextCount) {
  const trimmed = machines.slice(0, nextCount);

  if (trimmed.length >= nextCount) {
    return trimmed;
  }

  const expanded = [...trimmed];
  for (let index = expanded.length; index < nextCount; index += 1) {
    expanded.push(createDefaultMachine(index));
  }

  return expanded;
}

export default function MachineSettingsModal({ isOpen, initialMachines, onClose, onSave }) {
  const [draftMachines, setDraftMachines] = useState([]);
  const [draftCount, setDraftCount] = useState(1);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const seededMachines = initialMachines?.length ? initialMachines : [createDefaultMachine(0)];
    const normalized = seededMachines.map((machine, index) => ({
      id: machine.id || `preview-machine-${index + 1}`,
      name: machine.name || createDefaultMachine(index).name,
      type: machine.type === 'dryer' ? 'dryer' : 'washer',
      status: machine.status || 'available',
    }));

    const limitedCount = Math.max(1, Math.min(8, normalized.length));
    setDraftCount(limitedCount);
    setDraftMachines(resizeDraftMachines(normalized, limitedCount));
  }, [isOpen, initialMachines]);

  if (!isOpen) {
    return null;
  }

  function handleCountChange(event) {
    const nextCount = Math.max(1, Math.min(8, Number(event.target.value) || 1));
    setDraftCount(nextCount);
    setDraftMachines((current) => resizeDraftMachines(current, nextCount));
  }

  function handleMachineFieldChange(index, field, value) {
    setDraftMachines((current) =>
      current.map((machine, machineIndex) => {
        if (machineIndex !== index) {
          return machine;
        }

        return {
          ...machine,
          [field]: value,
        };
      }),
    );
  }

  function handleSave() {
    onSave(draftMachines.slice(0, draftCount));
  }

  return (
    <div className="machine-settings-modal__overlay" role="presentation" onClick={onClose}>
      <section
        className="machine-settings-modal__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="machine-settings-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="machine-settings-modal__header">
          <h2 id="machine-settings-modal-title" className="machine-settings-modal__title">Machine Settings</h2>
          <button type="button" className="machine-settings-modal__close" onClick={onClose} aria-label="Close machine settings">✕</button>
        </header>

        <label className="machine-settings-modal__count">
          <span>Machine count</span>
          <input type="number" min={1} max={8} value={draftCount} onChange={handleCountChange} />
        </label>

        <div className="machine-settings-modal__list">
          {draftMachines.map((machine, index) => (
            <article key={machine.id} className="machine-settings-modal__row">
              <p className="machine-settings-modal__row-title">Machine {index + 1}</p>
              <label>
                <span>Name</span>
                <input
                  type="text"
                  value={machine.name}
                  onChange={(event) => handleMachineFieldChange(index, 'name', event.target.value)}
                />
              </label>
              <label>
                <span>Type</span>
                <select value={machine.type} onChange={(event) => handleMachineFieldChange(index, 'type', event.target.value)}>
                  {MACHINE_TYPES.map((type) => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Status</span>
                <select value={machine.status} onChange={(event) => handleMachineFieldChange(index, 'status', event.target.value)}>
                  {MACHINE_STATUSES.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </label>
            </article>
          ))}
        </div>

        <footer className="machine-settings-modal__actions">
          <button type="button" className="machine-settings-modal__btn machine-settings-modal__btn--ghost" onClick={onClose}>Cancel</button>
          <button type="button" className="machine-settings-modal__btn machine-settings-modal__btn--primary" onClick={handleSave}>Save</button>
        </footer>
      </section>
    </div>
  );
}
