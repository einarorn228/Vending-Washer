import React from 'react';

export default function ErrorScreen({ message, inputMode }) {
  return (
    <section className="kiosk-screen kiosk-screen--error">
      <div className="kiosk-hero kiosk-hero--compact kiosk-hero--error">
        <p className="kiosk-hero__eyebrow">Attention</p>
        <h2 className="kiosk-hero__title">Unable to continue</h2>
        <p className="kiosk-hero__message">{message || 'Please ask an attendant for help.'}</p>
      </div>

      <div className="kiosk-detail-card kiosk-detail-card--status">
        <p className="kiosk-detail-card__title">What to do next</p>
        <p className="kiosk-detail-card__text">
          {inputMode === 'touch'
            ? 'Wait for backend reset, then scan your code again.'
            : 'Wait for hardware/backend reset, then scan your code again.'}
        </p>
      </div>
    </section>
  );
}
