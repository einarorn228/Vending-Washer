import React from 'react';

export default function HomeScreen({ message, inputMode }) {
  const isTouchMode = inputMode === 'touch';

  return (
    <section className="kiosk-screen kiosk-screen--home">
      <div className="kiosk-hero kiosk-hero--home">
        <p className="kiosk-hero__eyebrow">Ready to start</p>
        <h2 className="kiosk-hero__title">Scan your code</h2>
        <p className="kiosk-hero__message">{message || 'Scan your code to start your wash.'}</p>
      </div>

      <div className="kiosk-detail-card kiosk-detail-card--home">
        <p className="kiosk-detail-card__title">Next step</p>
        <p className="kiosk-detail-card__text">
          {isTouchMode
            ? 'After scanning, choose your machine directly on this screen.'
            : 'After scanning, use the hardware buttons to choose your machine.'}
        </p>
      </div>
    </section>
  );
}
