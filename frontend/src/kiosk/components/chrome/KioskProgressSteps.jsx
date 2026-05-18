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
  const activeIndex = resolveActiveIndex(currentState);
  const isError = currentState === 'error';

  return (
    <nav
      className={`kiosk-progress ${isError ? 'kiosk-progress--subdued' : ''}`}
      aria-label="Kiosk progress"
    >
      {STEPS.map((step, index) => {
        const isComplete = activeIndex !== null && index < activeIndex;
        const isActive = activeIndex !== null && index === activeIndex;

        return (
          <React.Fragment key={step}>
            <div
              className={`kiosk-progress__step ${isComplete ? 'kiosk-progress__step--complete' : ''} ${isActive ? 'kiosk-progress__step--active' : ''}`}
              aria-current={isActive ? 'step' : undefined}
            >
              <span className="kiosk-progress__dot" aria-hidden="true">
                {isComplete ? (
                  <svg
                    className="kiosk-progress__check"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M20 6L9 17L4 12"
                      stroke="currentColor"
                      strokeWidth="2.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  index + 1
                )}
              </span>
              <span className="kiosk-progress__label">{step}</span>
            </div>
            {index < STEPS.length - 1 ? (
              <span
                className={`kiosk-progress__line ${isComplete ? 'kiosk-progress__line--complete' : ''}`}
                aria-hidden="true"
              />
            ) : null}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
