import React from 'react';

const STEPS = ['Scan', 'Select', 'Start'];

function resolveActiveIndex(currentState) {
  switch (currentState) {
    case 'waiting_for_code':
      return 0;
    case 'choose_machine':
      return 1;
    case 'machine_starting':
    case 'machine_in_use':
      return 2;
    default:
      return null;
  }
}

export default function KioskProgressSteps({ currentState }) {
  if (currentState === 'error') {
    return null;
  }

  const activeIndex = resolveActiveIndex(currentState);

  return (
    <nav className="kiosk-progress" aria-label="Kiosk progress">
      {STEPS.map((step, index) => {
        const isComplete = activeIndex !== null && index < activeIndex;
        const isActive = activeIndex !== null && index === activeIndex;

        return (
          <React.Fragment key={step}>
            <div
              className={`kiosk-progress__step ${isComplete ? 'kiosk-progress__step--complete' : ''} ${isActive ? 'kiosk-progress__step--active' : ''}`}
              aria-current={isActive ? 'step' : undefined}
            >
              <span className="kiosk-progress__dot" aria-hidden="true" />
              <span className="kiosk-progress__label">{step}</span>
            </div>
            {index < STEPS.length - 1 ? <span className="kiosk-progress__line" aria-hidden="true" /> : null}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
