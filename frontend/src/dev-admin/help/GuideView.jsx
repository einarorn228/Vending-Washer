// frontend/src/dev-admin/help/GuideView.jsx
//
// Renders one compiled guide record. resolveLocale() (plain JS, tested in
// resolveLocale.test.js) picks which locale payload to show — a stub
// payload (no sections, no checks) never wins over a real one, so an
// Icelandic operator reading an untranslated guide sees the English content
// plus a visible notice, never a blank page.

import React from 'react';
import BlockRenderer from './BlockRenderer.jsx';
import { t } from './helpStrings.js';
import { resolveLocale } from './resolveLocale.js';

export default function GuideView({ guide, locale, onOpenGuide, titleFor }) {
  if (!guide) return null;

  const { locale: resolvedLocale, isFallback } = resolveLocale(guide, locale);
  const payload = guide.locales?.[resolvedLocale];
  if (!payload) return null;

  const sections = payload.sections || [];
  const relatedGuides = guide.related_guides || [];

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

      {/* Task 14 inserts the guide's checklist here, rendered from payload.checks
          against resolvedLocale, above the related-guides list below. */}

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

      {/* Task 14 inserts the support-report button here, using guide.id and
          resolvedLocale to prefill the escalation report. */}
    </div>
  );
}
