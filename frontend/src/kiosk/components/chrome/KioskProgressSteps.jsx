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

function CheckIcon() {
  return (
    <svg
      className="kiosk-progress__check-icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={3}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function TravelingLightning() {
  return (
    <div className="kiosk-progress__traveling-lightning-wrapper" aria-hidden="true">
      <svg
        viewBox="0 0 60 20"
        preserveAspectRatio="none"
        className="kiosk-progress__traveling-lightning-svg"
      >
        <path
          d="M5,10 L25,10 L35,10 L55,10"
          stroke="var(--kiosk-progress-energy-color)"
          fill="none"
          strokeWidth="8"
          opacity="0.3"
          filter="blur(3px)"
        />
        <path
          d="M0,10 L12,4 L22,15 L35,5 L45,14 L60,10"
          stroke="var(--kiosk-progress-energy-color)"
          fill="none"
          strokeWidth="2"
          opacity="0.8"
        />
        <path
          d="M5,10 L18,15 L28,5 L42,13 L52,7 L60,10"
          stroke="#ffffff"
          fill="none"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
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
        const isActive = !isError && activeIndex !== null && index === activeIndex;
        const isLineComplete = !isError && activeIndex !== null && index < activeIndex - 1;
        const isLineAnimating = !isError && activeIndex !== null && index === activeIndex - 1;

        return (
          <React.Fragment key={step}>
            <div
              className={`kiosk-progress__step-wrapper ${
                isComplete ? 'kiosk-progress__step-wrapper--complete' : ''
              } ${isActive ? 'kiosk-progress__step-wrapper--active' : ''}`}
              aria-current={isActive ? 'step' : undefined}
            >
              <div className="kiosk-progress__dot" aria-hidden="true">
                {isComplete ? <CheckIcon /> : index + 1}
              </div>
              <span className="kiosk-progress__label">{step}</span>
            </div>

            {index < STEPS.length - 1 ? (
              <div
                className={`kiosk-progress__line-wrapper ${
                  isLineComplete ? 'kiosk-progress__line--complete' : ''
                } ${isLineAnimating ? 'kiosk-progress__line--animating' : ''}`}
                aria-hidden="true"
              >
                {isLineAnimating ? <TravelingLightning /> : null}
              </div>
            ) : null}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
