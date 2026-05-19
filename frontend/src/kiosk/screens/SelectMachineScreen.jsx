import React, { useEffect, useRef, useState } from 'react';
import MachineGrid from '../components/machine/MachineGrid.jsx';
import { touchSelectMachine } from '../../api/backend.js';
import MachineIcon from '../components/machine/MachineIcon.jsx';

export default function SelectMachineScreen({ machines, message, interactionPolicy }) {
  const [selectionFeedback, setSelectionFeedback] = useState({ message: '', tone: 'info' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const feedbackTimerRef = useRef(null);

  const isTouchSelectable = Boolean(interactionPolicy?.allowTouchMachineSelect);


  useEffect(() => {
    return () => {
      if (feedbackTimerRef.current) {
        clearTimeout(feedbackTimerRef.current);
      }
    };
  }, []);

  function showFeedback(messageText, tone = 'info') {
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
    }

    setSelectionFeedback({ message: messageText, tone });

    const hideDelay = tone === 'error' ? 4000 : 3000;
    feedbackTimerRef.current = setTimeout(() => {
      setSelectionFeedback({ message: '', tone: 'info' });
      feedbackTimerRef.current = null;
    }, hideDelay);
  }

  async function handleMachineSelect(machine) {
    if (!isTouchSelectable || isSubmitting || !machine?.id) {
      return;
    }

    setIsSubmitting(true);
    showFeedback('Selecting machine...', 'info');

    const result = await touchSelectMachine(machine.id);

    if (result?.success) {
      showFeedback(result.message || 'Machine enabled. Waiting for backend update...', 'success');
    } else {
      showFeedback(result?.message || 'Unable to select machine right now.', 'error');
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

      {selectionFeedback.message ? (
        <div className="kiosk-select-feedback-wrap">
          <div
            className={`kiosk-select-feedback kiosk-select-feedback--${selectionFeedback.tone}`}
            role={selectionFeedback.tone === 'error' ? 'alert' : 'status'}
            aria-live="polite"
          >
            {selectionFeedback.message}
          </div>
        </div>
      ) : null}
    </section>
  );
}
