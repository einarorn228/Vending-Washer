// frontend/src/dev-admin/help/HelpPanel.jsx
//
// The Help tab. Driven entirely by `helpRoute` (parsed from
// window.location.hash by DevAdminPage via parseHelpHash) — navigation here
// writes the hash via formatHelpHash so a refresh on a kiosk tablet lands
// back on the same guide. This is the OTHER half of the Help Hub: the
// drawer (HelpDrawer.jsx) is driven by page state and never touches the
// hash. The two must stay independent.

import React, { useMemo, useState } from 'react';
import GuideView from './GuideView.jsx';
import HelpErrorBoundary from './HelpErrorBoundary.jsx';
import { useHelpManifest } from './useHelpManifest.js';
import { searchGuides } from './helpSearch.js';
import { commonProblems } from './commonProblems.js';
import { formatHelpHash } from './helpRouting.js';
import { t, STRINGS } from './helpStrings.js';

function makeTitleFor(manifest, locale) {
  return (id) => {
    const guide = manifest?.guides?.[id];
    if (!guide) return id;
    const payload = guide.locales?.[locale] || guide.locales?.[guide.canonical_locale];
    return payload?.title || id;
  };
}

function summaryFor(manifest, locale, guideId) {
  const guide = manifest?.guides?.[guideId];
  if (!guide) return '';
  const payload = guide.locales?.[locale] || guide.locales?.[guide.canonical_locale];
  return payload?.summary || '';
}

// Frozen category vocabulary, ordered by first appearance in the manifest
// (spec: "Order categories by first appearance in Object.values(manifest.guides)").
function buildCategories(manifest, titleFor) {
  const order = [];
  const seen = new Set();
  const byCategory = {};
  for (const guide of Object.values(manifest?.guides || {})) {
    if (!seen.has(guide.category)) {
      seen.add(guide.category);
      order.push(guide.category);
    }
    (byCategory[guide.category] = byCategory[guide.category] || []).push(guide);
  }
  return order.map((categoryId) => ({
    id: categoryId,
    guides: [...(byCategory[categoryId] || [])].sort((a, b) =>
      titleFor(a.id).localeCompare(titleFor(b.id)),
    ),
  }));
}

function navigateToGuide(guideId, anchor) {
  if (typeof window === 'undefined') return;
  window.location.hash = formatHelpHash(guideId, anchor);
}

function navigateToLanding() {
  if (typeof window === 'undefined') return;
  window.location.hash = 'help';
}

function LocaleToggle({ locale, onLocaleChange }) {
  return (
    <div className="dev-admin-helphub-locale" role="group" aria-label="Help language">
      {Object.keys(STRINGS).map((code) => (
        <button
          key={code}
          type="button"
          className={locale === code ? 'is-active' : ''}
          aria-pressed={locale === code}
          onClick={() => onLocaleChange?.(code)}
        >
          {code}
        </button>
      ))}
    </div>
  );
}

function SearchResults({ query, manifest, locale, titleFor }) {
  const results = searchGuides(query, manifest, locale);
  if (results.length === 0) {
    return <p className="dev-admin-save-message">{t(locale, 'noResults')}</p>;
  }
  return (
    <ul className="dev-admin-helphub-search-results">
      {results.map(({ guideId }) => (
        <li key={guideId}>
          <button
            type="button"
            className="dev-admin-guide-link"
            onClick={() => navigateToGuide(guideId, null)}
          >
            {titleFor(guideId)}
          </button>
          <p className="dev-admin-helphub-search-summary">{summaryFor(manifest, locale, guideId)}</p>
        </li>
      ))}
    </ul>
  );
}

export default function HelpPanel({ apiKey, helpRoute, locale: preferredLocale, onLocaleChange, machineId }) {
  const { manifest, error, loading } = useHelpManifest(apiKey);
  const [query, setQuery] = useState('');

  // The stored/preferred locale is only ever passed to GuideView or the
  // support-report body after being constrained to the manifest's own
  // `locales` list — an unknown or stale stored value falls back to the
  // manifest's default_locale (or 'is' before the manifest has loaded).
  const locale = useMemo(() => {
    const allowed = manifest?.locales || ['is', 'en'];
    return allowed.includes(preferredLocale) ? preferredLocale : (manifest?.default_locale || 'is');
  }, [manifest, preferredLocale]);

  const titleFor = useMemo(() => makeTitleFor(manifest, locale), [manifest, locale]);

  if (error) {
    return (
      <section className="dev-admin-panel">
        <h2>{t(locale, 'help')}</h2>
        <p className="dev-admin-warning dev-admin-helphub-unavailable">{t(locale, 'unavailable')}</p>
      </section>
    );
  }

  if (loading || !manifest) {
    return (
      <section className="dev-admin-panel">
        <h2>{t(locale, 'help')}</h2>
      </section>
    );
  }

  const guide = helpRoute.guideId ? manifest.guides?.[helpRoute.guideId] : null;

  if (helpRoute.guideId && (helpRoute.invalid || !guide)) {
    return (
      <section className="dev-admin-panel">
        <div className="dev-admin-panel__header">
          <h2>{t(locale, 'help')}</h2>
          <LocaleToggle locale={locale} onLocaleChange={onLocaleChange} />
        </div>
        <p className="dev-admin-helphub-notfound">{t(locale, 'notFound')}</p>
        <button type="button" className="dev-admin-guide-link" onClick={navigateToLanding}>
          {t(locale, 'guides')}
        </button>
      </section>
    );
  }

  if (guide) {
    return (
      <section className="dev-admin-panel">
        <div className="dev-admin-panel__header">
          <button type="button" className="dev-admin-guide-link" onClick={navigateToLanding}>
            ← {t(locale, 'guides')}
          </button>
          <LocaleToggle locale={locale} onLocaleChange={onLocaleChange} />
        </div>
        <GuideView
          guide={guide}
          locale={locale}
          onOpenGuide={navigateToGuide}
          titleFor={titleFor}
          apiKey={apiKey}
          machineId={machineId}
        />
      </section>
    );
  }

  const categories = buildCategories(manifest, titleFor);
  const problems = commonProblems(manifest, locale);
  const trimmedQuery = query.trim();

  return (
    <section className="dev-admin-panel">
      <div className="dev-admin-panel__header">
        <h2>{t(locale, 'help')}</h2>
        <LocaleToggle locale={locale} onLocaleChange={onLocaleChange} />
      </div>

      <input
        type="search"
        className="dev-admin-filter dev-admin-helphub-search"
        placeholder={t(locale, 'searchPlaceholder')}
        aria-label={t(locale, 'searchPlaceholder')}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      {trimmedQuery ? (
        <HelpErrorBoundary locale={locale} resetKey={`${trimmedQuery}:${locale}`}>
          <SearchResults query={trimmedQuery} manifest={manifest} locale={locale} titleFor={titleFor} />
        </HelpErrorBoundary>
      ) : null}

      {problems.length > 0 ? (
        <article className="dev-admin-group-card dev-admin-helphub-common-problems">
          <h3>{t(locale, 'commonProblems')}</h3>
          <ul className="dev-admin-helphub-guide-list">
            {problems.map(({ guideId, title }) => (
              <li key={guideId}>
                <button type="button" className="dev-admin-guide-link" onClick={() => navigateToGuide(guideId, null)}>
                  {title}
                </button>
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      {categories.map((category) => (
        <article key={category.id} className="dev-admin-group-card dev-admin-helphub-category">
          <h3>{t(locale, `category_${category.id}`) || category.id}</h3>
          <ul className="dev-admin-helphub-guide-list">
            {category.guides.map((categoryGuide) => (
              <li key={categoryGuide.id}>
                <button
                  type="button"
                  className="dev-admin-guide-link"
                  onClick={() => navigateToGuide(categoryGuide.id, null)}
                >
                  {titleFor(categoryGuide.id)}
                </button>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
