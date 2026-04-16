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
    setSelectionMessage('Selecting machine…');

    const result = await touchSelectMachine(machine.id);

    if (result?.success) {
      setSelectionMessage(result.message || 'Machine selected. Waiting for backend update…');
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
              ? 'Tap an available machine card to start.'
              : 'Use the hardware buttons to choose an available machine.')}
        </p>
      </div>

      <MachineGrid
        machines={machines}
        isInteractive={isTouchSelectable}
        onSelect={handleMachineSelect}
      />

      <div className="kiosk-detail-card kiosk-detail-card--status">
        <p className="kiosk-detail-card__title">Selection status</p>
        <p className="kiosk-detail-card__text">
          {selectionMessage ||
            (isTouchSelectable
              ? 'Touch mode is active. Tap a machine to continue.'
              : 'Hardware mode is active. Use machine buttons to continue.')}
        </p>
      </div>
    </section>
  );
}
