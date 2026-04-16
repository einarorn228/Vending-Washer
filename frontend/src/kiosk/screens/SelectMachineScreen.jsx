import React, { useState } from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';
import { touchSelectMachine } from '../../api/backend.js';

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
    <section className="kiosk-screen kiosk-screen--select-machine">
      <div className="kiosk-hero kiosk-hero--compact">
        <p className="kiosk-hero__eyebrow">Machine selection</p>
        <h2 className="kiosk-hero__title">Choose your machine</h2>
        <p className="kiosk-hero__message">
          {message ||
            (isTouchSelectable
              ? 'Tap an available machine to continue.'
              : 'Use the hardware buttons to choose an available machine.')}
        </p>
      </div>

      <MachineGrid
        machines={machines}
        isInteractive={isTouchSelectable}
        onSelect={handleMachineSelect}
      />

      <div className="kiosk-toast" role="status" aria-live="polite">
        {selectionMessage ||
          (isTouchSelectable
            ? 'Touch mode active. Tap a machine card to continue.'
            : 'Hardware mode active. Screen is read-only in this step.')}
      </div>
    </section>
  );
}
