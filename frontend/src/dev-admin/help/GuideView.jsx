// frontend/src/dev-admin/help/GuideView.jsx
//
// Renders one compiled guide record. resolveLocale() (plain JS, tested in
// resolveLocale.test.js) picks which locale payload to show — a stub
// payload (no sections, no checks) never wins over a real one, so an
// Icelandic operator reading an untranslated guide sees the English content
// plus a visible notice, never a blank page.

import React, { useEffect, useState } from 'react';
import BlockRenderer from './BlockRenderer.jsx';
import ChecklistPanel from './ChecklistPanel.jsx';
import SupportReportButton from './SupportReportButton.jsx';
import { t } from './helpStrings.js';
import { resolveLocale } from './resolveLocale.js';
import { initialCheckState, setCheckResult, toReportChecks } from './checklistState.js';

export default function GuideView({ guide, locale, onOpenGuide, titleFor, apiKey, machineId }) {
  const { locale: resolvedLocale, isFallback } = resolveLocale(guide, locale);
  const payload = guide?.locales?.[resolvedLocale];
  const checks = payload?.checks || [];

  const [checkState, setCheckState] = useState(() => initialCheckState(checks));

  useEffect(() => {
    setCheckState(initialCheckState(checks));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guide?.id, resolvedLocale]);

  if (!guide || !payload) return null;

  const sections = payload.sections || [];
  const relatedGuides = guide.related_guides || [];

  const handleSetResult = (checkId, result) => {
    setCheckState((prev) => setCheckResult(prev, checkId, result));
  };

  return (
    <div className="dev-admin-guide-view">
      <div className="dev-admin-guide-view__head">
        <h2>{payload.title}</h2>
        {guide.risk === 'high' ? (
          <span className="dev-admin-badge dev-admin-badge--high dev-admin-guide-view__risk">
            {t(locale, 'riskHigh')}
          </span>
        ) : null}
      </div>

      {isFallback ? (
        <p className="dev-admin-warning dev-admin-guide-view__fallback">
          {t(locale, 'fallbackNotice')}
        </p>
      ) : null}

      {sections.map((section, index) => (
        <section key={section.anchor || `section-${index}`} id={section.anchor || undefined}>
          {section.heading ? <h3>{section.heading}</h3> : null}
          <BlockRenderer blocks={section.blocks} onOpenGuide={onOpenGuide} />
        </section>
      ))}

      {checks.length > 0 ? (
        <ChecklistPanel
          checks={checks}
          state={checkState}
          onSetResult={handleSetResult}
          locale={locale}
          onOpenGuide={onOpenGuide}
          titleFor={titleFor}
        />
      ) : null}

      {relatedGuides.length > 0 ? (
        <section className="dev-admin-guide-view__related">
          <h3>{t(locale, 'relatedGuides')}</h3>
          <div className="dev-admin-guide-view__related-list">
            {relatedGuides.map((guideId) => (
              <button
                key={guideId}
                type="button"
                className="dev-admin-guide-view__related-link"
                onClick={() => onOpenGuide?.(guideId, null)}
              >
                {titleFor ? titleFor(guideId) : guideId}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <SupportReportButton
        apiKey={apiKey}
        guideId={guide.id}
        machineId={machineId}
        checks={toReportChecks(checkState)}
        locale={locale}
      />
    </div>
  );
}
