// frontend/src/public-help/PublicHelpPage.jsx
//
// Public bootstrap help tier at /help. Renders from the statically imported,
// build-time-compiled public manifest with NO network call of any kind — no
// polling hook, no API import — because the entire point of this tier is
// that it works while the backend is completely down. Do not import
// anything from frontend/src/api/ or frontend/src/dev-admin/help/useHelpManifest.js
// here; that would defeat the tier.
//
// Content is restricted by review + backend/tests/test_help_artifacts.py to
// three non-privileged guides (docs/public-help/*.md). The lockout line
// below is fixed page chrome, not guide content, so it is visible whichever
// guide is open (or none).

import React, { useEffect, useState } from 'react';
import BlockRenderer from '../dev-admin/help/BlockRenderer.jsx';
import { resolveLocale } from '../dev-admin/help/resolveLocale.js';
import manifest from '../generated/public-help-manifest.json';
import '../dev-admin/styles/dev-admin.css';
import './public-help.css';

const LOCALE = 'is';

function guideIdFromHash() {
  if (typeof window === 'undefined') return null;
  const raw = window.location.hash.replace(/^#/, '');
  return raw || null;
}

function GuideList({ guides, onOpenGuide }) {
  return (
    <ul className="dev-admin-helphub-guide-list public-help-guide-list">
      {guides.map((guide) => {
        const payload = guide.locales[resolveLocale(guide, LOCALE).locale];
        return (
          <li key={guide.id}>
            <button
              type="button"
              className="dev-admin-guide-link"
              onClick={() => onOpenGuide(guide.id)}
            >
              {payload?.title || guide.id}
            </button>
            <p className="public-help-guide-summary">{payload?.summary}</p>
          </li>
        );
      })}
    </ul>
  );
}

function GuideView({ guide, onBack }) {
  const { locale: resolvedLocale } = resolveLocale(guide, LOCALE);
  const payload = guide.locales[resolvedLocale];
  const sections = payload?.sections || [];

  return (
    <div className="dev-admin-guide-view">
      <button type="button" className="dev-admin-guide-link public-help-back" onClick={onBack}>
        ← Til baka
      </button>
      <h2>{payload?.title}</h2>
      {sections.map((section, index) => (
        <section key={section.anchor || `section-${index}`} id={section.anchor || undefined}>
          {section.heading ? <h3>{section.heading}</h3> : null}
          <BlockRenderer blocks={section.blocks} />
        </section>
      ))}
    </div>
  );
}

export default function PublicHelpPage() {
  const [guideId, setGuideId] = useState(guideIdFromHash);

  useEffect(() => {
    const onHashChange = () => setGuideId(guideIdFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const openGuide = (id) => {
    window.location.hash = id;
  };

  const goBack = () => {
    window.location.hash = '';
    setGuideId(null);
  };

  const guides = Object.values(manifest.guides);
  const activeGuide = guideId ? manifest.guides[guideId] : null;

  return (
    <div className="dev-admin-page public-help">
      <div className="dev-admin-panel public-help-panel">
        <h1>Hjálp</h1>

        {activeGuide ? (
          <GuideView guide={activeGuide} onBack={goBack} />
        ) : (
          <GuideList guides={guides} onOpenGuide={openGuide} />
        )}

        <div className="public-help-lockout">
          <h3>Stjórnandaaðgangur</h3>
          <p>Stjórnandaaðgangur er ekki tiltækur. Hafðu samband við kerfisstjóra.</p>
        </div>
      </div>
    </div>
  );
}
