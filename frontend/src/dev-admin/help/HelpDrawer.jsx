// frontend/src/dev-admin/help/HelpDrawer.jsx
//
// Overlay wrapper around GuideView, opened by ContextualHelpLink through
// HelpDrawerContext. Driven only by page state (guideId/anchor/machineId
// passed down from DevAdminPage's drawerGuide) — it never reads or writes
// window.location.hash, so the tab underneath (and any unsaved draft in it)
// stays mounted and untouched. Opening a related guide, a guide_link, or a
// checklist problem_guide from inside the drawer swaps the drawer's guide
// via onNavigate; it never leaves the drawer.

import React, { useEffect, useMemo } from 'react';
import GuideView from './GuideView.jsx';
import { useHelpManifest } from './useHelpManifest.js';
import { t } from './helpStrings.js';
import { makeTitleFor } from './guideTitle.js';

export default function HelpDrawer({ guideId, anchor, machineId, apiKey, locale: preferredLocale, onClose, onNavigate }) {
  const { manifest, error, loading } = useHelpManifest(apiKey);

  // Same clamp as HelpPanel: a stale/unknown stored locale falls back to the
  // manifest's default_locale before it ever reaches GuideView or the
  // support-report body.
  const locale = useMemo(() => {
    const allowed = manifest?.locales || ['is', 'en'];
    return allowed.includes(preferredLocale) ? preferredLocale : (manifest?.default_locale || 'is');
  }, [manifest, preferredLocale]);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose?.();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const titleFor = useMemo(() => makeTitleFor(manifest, locale), [manifest, locale]);

  const guide = manifest?.guides?.[guideId];

  let body;
  if (error) {
    body = <p className="dev-admin-warning dev-admin-helphub-unavailable">{t(locale, 'unavailable')}</p>;
  } else if (loading) {
    body = <p className="dev-admin-save-message">{t(locale, 'help')}…</p>;
  } else if (!guide) {
    body = <p className="dev-admin-helphub-notfound">{t(locale, 'notFound')}</p>;
  } else {
    body = (
      <GuideView
        guide={guide}
        locale={locale}
        onOpenGuide={(nextGuideId, nextAnchor) => onNavigate?.(nextGuideId, nextAnchor)}
        titleFor={titleFor}
        apiKey={apiKey}
        machineId={machineId}
        anchor={anchor}
      />
    );
  }

  return (
    <div className="dev-admin-drawer__overlay" role="presentation" onClick={onClose}>
      <aside
        className="dev-admin-drawer dev-admin-helphub-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="dev-admin-drawer__header">
          <div>
            <p className="dev-admin-eyebrow">{t(locale, 'help')}</p>
            <h2 id="help-drawer-title">{guide ? titleFor(guideId) : t(locale, 'help')}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close">✕</button>
        </header>

        {body}
      </aside>
    </div>
  );
}
