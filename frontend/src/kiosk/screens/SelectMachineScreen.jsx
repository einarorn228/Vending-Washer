import React, { useState } from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';
import { touchSelectMachine } from '../../api/backend.js';
import MachineIcon from '../components/machine/MachineIcon.jsx';

export default function SelectMachineScreen({ machines, message, interactionPolicy }) {
  const [selectionMessage, setSelectionMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isTouchSelectable = Boolean(interactionPolicy?.allowTouchMachineSelect);

  async function handleMachineSelect(machine) {
    if (!isTouchSelectable || isSubmitting || !machine?.id) {
      return;
    }

    setIsSubmitting(true);
    setSelectionMessage('Selecting machine...');

    const result = await touchSelectMachine(machine.id);

    if (result?.success) {
      setSelectionMessage(result.message || 'Machine enabled. Waiting for backend update...');
    } else {
      setSelectionMessage(result?.message || 'Unable to select machine right now.');
    }

    setIsSubmitting(false);
  }

  return (
    <section className="kiosk-screen kiosk-screen--select-machine kiosk-screen--select">
      <div className="kiosk-stage-card kiosk-stage-card--hero kiosk-hero kiosk-hero--compact kiosk-flow-hero kiosk-flow-hero--select">
        <div className="kiosk-flow-hero__icon" aria-hidden="true">
          <MachineIcon type="washer" className="kiosk-flow-hero__machine-icon" />
        </div>
        <p className="kiosk-hero__eyebrow">Machine selection</p>
        <h2 className="kiosk-hero__title">Choose your machine</h2>
        <p className="kiosk-hero__message">
          {message ||
            (isTouchSelectable
              ? 'Code accepted. Choose any available machine.'
              : 'Code accepted. Ask an attendant to choose an available machine.')}
        </p>
      </div>

      <MachineGrid
        machines={machines}
        isInteractive={isTouchSelectable}
        onSelect={handleMachineSelect}
        variant="default"
      />

      <div className="kiosk-stage-card kiosk-support-card kiosk-toast" role="status" aria-live="polite">
        {selectionMessage ||
          (isTouchSelectable
            ? 'Tap a machine card to continue.'
            : 'Waiting for assisted machine selection.')}
      </div>
    </section>
  );
}
