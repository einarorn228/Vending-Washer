// frontend/src/dev-admin/help/ContextualHelpLink.jsx
//
// A small "?" button placed next to a page element (a Settings group header,
// a drawer title, a warning banner) that opens the Help drawer over whatever
// is currently on screen. It NEVER touches window.location.hash and never
// switches tabs, so unsaved Settings drafts, Machine Card edits, and
// in-progress technical mapping survive opening Help. Outside a
// HelpDrawerContext provider it renders nothing.
//
// Accessible name: callsites pass `labelKey` (a helpStrings.js key for a
// fixed, already-bilingual string) or `labelSuffix` (appended after the
// localized "Help:" prefix, for a caller-supplied bit of text such as a
// Settings group title that is out of scope for Help Hub translation). The
// locale itself comes from HelpDrawerContext — the same value HelpPanel and
// HelpDrawer render with — so no callsite has to know or pass it. `label` is
// kept as an escape hatch for a literal, pre-resolved string.

import React from 'react';
import { useHelpDrawer } from './HelpDrawerContext.js';
import { t } from './helpStrings.js';

export default function ContextualHelpLink({ guideId, anchor, label, labelKey, labelSuffix, machineId, locale }) {
  const helpDrawer = useHelpDrawer();
  if (!helpDrawer) return null;

  const resolvedLocale = locale || helpDrawer.locale || 'en';
  const resolvedLabel = label
    || (labelKey && t(resolvedLocale, labelKey))
    || (labelSuffix && `${t(resolvedLocale, 'help')}: ${labelSuffix}`)
    || t(resolvedLocale, 'help');

  function handleClick() {
    if (machineId) {
      helpDrawer.openHelpDrawer(guideId, anchor || null, { machineId });
    } else {
      helpDrawer.openHelpDrawer(guideId, anchor || null);
    }
  }

  return (
    <button
      type="button"
      className="dev-admin-helphub-link"
      aria-label={resolvedLabel}
      title={resolvedLabel}
      onClick={handleClick}
    >
      ?
    </button>
  );
}
