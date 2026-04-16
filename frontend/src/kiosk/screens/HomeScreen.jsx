import React from 'react';

export default function HomeScreen({ message, inputMode }) {
  const isTouchMode = inputMode === 'touch';

  return (
    <section className="kiosk-screen kiosk-screen--home">
      <div className="kiosk-hero kiosk-hero--home">
        <div className="kiosk-scan-mark" aria-hidden="true">
          <span className="kiosk-scan-mark__frame" />
          <span className="kiosk-scan-mark__frame" />
          <span className="kiosk-scan-mark__frame" />
          <span className="kiosk-scan-mark__frame" />
          <span className="kiosk-scan-mark__code" />
        </div>
        <p className="kiosk-hero__eyebrow">Ready to start</p>
        <h2 className="kiosk-hero__title">Scan your code</h2>
        <p className="kiosk-hero__message">{message || 'Hold your code in front of the scanner.'}</p>
      </div>

      <div className="kiosk-detail-card kiosk-detail-card--home">
        <p className="kiosk-detail-card__title">Next step</p>
        <p className="kiosk-detail-card__text">
          {isTouchMode
            ? 'After scanning, choose your machine on the screen.'
            : 'After scanning, choose your machine with the hardware buttons.'}
        </p>
      </div>
    </section>
  );
}
