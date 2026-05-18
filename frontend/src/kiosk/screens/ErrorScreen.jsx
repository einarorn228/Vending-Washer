import React from 'react';

export default function ErrorScreen({ message, inputMode }) {
  return (
    <section className="kiosk-screen kiosk-screen--error">
      <div className="kiosk-stage-card kiosk-stage-card--hero kiosk-stage-card--error kiosk-hero kiosk-hero--compact kiosk-hero--error">
        <p className="kiosk-hero__eyebrow">System alert</p>
        <h2 className="kiosk-hero__title">Unable to continue</h2>
        <p className="kiosk-hero__message">{message || 'Please ask an attendant for help.'}</p>
      </div>

      <div className="kiosk-stage-card kiosk-support-card kiosk-detail-card kiosk-detail-card--status kiosk-detail-card--error-next">
        <p className="kiosk-detail-card__title">Next step</p>
        <p className="kiosk-detail-card__text">
          {inputMode === 'touch'
            ? 'Please wait for reset, then scan your code again.'
            : 'Wait for hardware reset, then scan your code again.'}
        </p>
      </div>
    </section>
  );
}
