import React, { useEffect, useMemo, useState } from 'react';
import MachineGrid from '../../kiosk/components/machine/MachineGrid.jsx';
import { saveDevAdminMachines } from '../api.js';
import MachineDetailDrawer from './MachineDetailDrawer.jsx';

function cloneMachines(machines) {
  return (machines || []).map((machine) => ({ ...machine, technical: { ...(machine.technical || {}) } }));
}

function toPreviewMachine(machine) {
  return {
    id: machine.machine_key,
    name: machine.display_name,
    type: machine.type,
    short_label: machine.short_label,
    description: machine.description,
    available: true,
    status: machine.active_in_kiosk ? 'available' : 'unavailable',
  };
}

export default function MachineCardsPanel({ apiKey, machines, onReload }) {
  const [draft, setDraft] = useState(() => cloneMachines(machines));
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(cloneMachines(machines));
    setErrors({});
  }, [machines]);

  const previewMachines = useMemo(() => draft.filter((machine) => machine.active_in_kiosk).map(toPreviewMachine), [draft]);

  function updateMachine(index, field, value) {
    setDraft((current) => current.map((machine, i) => (i === index ? { ...machine, [field]: value } : machine)));
  }

  function moveMachine(index, direction) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= draft.length) return;
    setDraft((current) => {
      const next = [...current];
      const [item] = next.splice(index, 1);
      next.splice(nextIndex, 0, item);
      return next.map((machine, i) => ({ ...machine, display_order: i + 1 }));
    });
  }

  function machineChanged(machine, original) {
    if (!original) return true;
    return ['display_name', 'short_label', 'type', 'description', 'active_in_kiosk', 'display_order'].some(
      (field) => JSON.stringify(machine[field]) !== JSON.stringify(original[field]),
    );
  }

  async function handleSave() {
    setSaving(true);
    setErrors({});
    setMessage('');
    const originalByKey = Object.fromEntries((machines || []).map((machine) => [machine.machine_key, machine]));
    const order = draft.map((machine) => machine.machine_key);
    const originalOrder = (machines || []).map((machine) => machine.machine_key);

    const orderChanged = JSON.stringify(order) !== JSON.stringify(originalOrder);
    const updates = draft
      .filter((machine) => machineChanged(machine, originalByKey[machine.machine_key]))
      .map((machine) => ({
        machine_key: machine.machine_key,
        display_name: machine.display_name,
        short_label: machine.short_label,
        type: machine.type,
        description: machine.description,
        active_in_kiosk: machine.active_in_kiosk,
        display_order: machine.display_order,
      }));

    if (!updates.length && !orderChanged) {
      setSaving(false);
      setMessage('No changes to save.');
      return;
    }

    // One request, one backend transaction: a rejected card can no longer leave the
    // machines before it already written.
    const result = await saveDevAdminMachines(apiKey, updates, orderChanged ? order : null);
    setSaving(false);

    if (!result.ok || !result.payload?.success) {
      const payloadErrors = { ...(result.payload?.errors || {}) };
      // The order/generic errors render through the `layout` slot above the list.
      if (payloadErrors.order) {
        payloadErrors.layout = payloadErrors.order.order || 'Machine order save failed.';
        delete payloadErrors.order;
      }
      if (payloadErrors.updates) {
        payloadErrors.layout = Object.values(payloadErrors.updates)[0] || 'Machine save failed.';
        delete payloadErrors.updates;
      }
      if (!Object.keys(payloadErrors).length) {
        payloadErrors.layout = result.payload?.message || 'Machine save failed.';
      }
      setErrors(payloadErrors);
      setMessage('Nothing was saved. Fix the errors below and save again.');
      return;
    }

    setMessage('Machine card layout saved. Reloading current values…');
    onReload();
  }

  return (
    <section className="dev-admin-panel">
      <div className="dev-admin-panel__header">
        <div>
          <p className="dev-admin-eyebrow">Preview-only kiosk layout</p>
          <h2>Machine Cards</h2>
        </div>
        <div className="dev-admin-actions">
          <button type="button" onClick={() => setDraft(cloneMachines(machines))}>Discard</button>
          <button type="button" className="dev-admin-primary" disabled={saving} onClick={handleSave}>{saving ? 'Saving…' : 'Save machine cards'}</button>
        </div>
      </div>

      <div className="dev-admin-warning">
        Preview only — clicking these cards will not select/start machines or change live kiosk state. “Active in kiosk” removes/restores the machine in the selection/runtime flow, not just visually.
      </div>

      <div className="dev-admin-machine-preview" onClick={(event) => event.stopPropagation()}>
        <MachineGrid machines={previewMachines} isInteractive={false} onSelect={undefined} variant="default" />
      </div>

      {errors.layout ? <p className="dev-admin-form-error">{errors.layout}</p> : null}

      <div className="dev-admin-machine-list">
        {draft.map((machine, index) => {
          const rowErrors = errors[machine.machine_key] || {};
          return (
            <article key={machine.machine_key} className="dev-admin-machine-row">
              <div className="dev-admin-machine-row__order">
                <button type="button" disabled={index === 0} onClick={() => moveMachine(index, -1)}>↑</button>
                <strong>{index + 1}</strong>
                <button type="button" disabled={index === draft.length - 1} onClick={() => moveMachine(index, 1)}>↓</button>
              </div>
              <label>Display name<input value={machine.display_name} onChange={(e) => updateMachine(index, 'display_name', e.target.value)} />{rowErrors.display_name ? <span>{rowErrors.display_name}</span> : null}</label>
              <label>Short label<input value={machine.short_label || ''} onChange={(e) => updateMachine(index, 'short_label', e.target.value)} />{rowErrors.short_label ? <span>{rowErrors.short_label}</span> : null}</label>
              <label>Type<select value={machine.type} onChange={(e) => updateMachine(index, 'type', e.target.value)}><option value="washer">washer</option><option value="dryer">dryer</option></select>{rowErrors.type ? <span>{rowErrors.type}</span> : null}</label>
              <label className="dev-admin-toggle-row"><input type="checkbox" checked={Boolean(machine.active_in_kiosk)} onChange={(e) => updateMachine(index, 'active_in_kiosk', e.target.checked)} /> Active in kiosk<span>Show and allow selection/runtime flow</span></label>
              <button type="button" className="dev-admin-secondary" onClick={() => setSelectedMachine(machine)}>Advanced / Technical Mapping</button>
            </article>
          );
        })}
      </div>
      {message ? <p className="dev-admin-save-message">{message}</p> : null}
      {selectedMachine ? (
        <MachineDetailDrawer
          apiKey={apiKey}
          machine={selectedMachine}
          onClose={() => setSelectedMachine(null)}
          onSaved={() => { setSelectedMachine(null); onReload(); }}
        />
      ) : null}
    </section>
  );
}
