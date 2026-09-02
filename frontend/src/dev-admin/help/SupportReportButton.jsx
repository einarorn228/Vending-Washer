// frontend/src/dev-admin/help/SupportReportButton.jsx
//
// Assembles and copies an escalation report for the current guide + checklist
// evidence. `locale_shown` is server-owned (Task 10) — the request body never
// includes it, and the backend derives it from the resolved guide. On a
// non-ok response the server's plain-text `message` is shown verbatim; never
// HTML, never a thrown error.

import React, { useEffect, useRef, useState } from 'react';
import { requestSupportReport } from '../api.js';
import { t } from './helpStrings.js';
import { buildSupportReportBody } from './checklistState.js';

export default function SupportReportButton({ apiKey, guideId, machineId, checks, locale }) {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null); // null | 'copied' | 'manual' | { error: string }
  const [reportText, setReportText] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (status === 'manual' && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [status, reportText]);

  const handleClick = async () => {
    setBusy(true);
    setStatus(null);
    try {
      const body = buildSupportReportBody({ guideId, machineId, checks, locale });
      const { ok, payload } = await requestSupportReport(apiKey, body);
      if (!ok || !payload?.success) {
        setStatus({ error: payload?.message || 'Unable to build report.' });
        return;
      }

      const text = payload.text || '';
      setReportText(text);

      let copied = false;
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(text);
          copied = true;
        } catch {
          copied = false;
        }
      }
      setStatus(copied ? 'copied' : 'manual');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="dev-admin-guide-report">
      <button
        type="button"
        className="dev-admin-primary dev-admin-guide-report__button"
        onClick={handleClick}
        disabled={busy}
      >
        {t(locale, 'copyReport')}
      </button>

      {status === 'copied' ? (
        <p className="dev-admin-guide-report__status">{t(locale, 'reportCopied')}</p>
      ) : null}

      {status === 'manual' ? (
        <textarea
          ref={textareaRef}
          className="dev-admin-guide-report__textarea"
          readOnly
          value={reportText}
          onFocus={(event) => event.target.select()}
        />
      ) : null}

      {status && typeof status === 'object' && status.error ? (
        <p className="dev-admin-warning dev-admin-guide-report__status">{status.error}</p>
      ) : null}
    </div>
  );
}
