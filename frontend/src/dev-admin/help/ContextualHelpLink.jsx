// frontend/src/dev-admin/help/ContextualHelpLink.jsx
//
// A small "?" button placed next to a page element (a Settings group header,
// a drawer title, a warning banner) that opens the Help drawer over whatever
// is currently on screen. It NEVER touches window.location.hash and never
// switches tabs, so unsaved Settings drafts, Machine Card edits, and
// in-progress technical mapping survive opening Help. Outside a
// HelpDrawerContext provider it renders nothing.

import React from 'react';
import { useHelpDrawer } from './HelpDrawerContext.js';
import { t } from './helpStrings.js';

export default function ContextualHelpLink({ guideId, anchor, label, machineId, locale = 'en' }) {
  const helpDrawer = useHelpDrawer();
  if (!helpDrawer) return null;

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
      aria-label={label || t(locale, 'help')}
      title={label || t(locale, 'help')}
      onClick={handleClick}
    >
      ?
    </button>
  );
}
