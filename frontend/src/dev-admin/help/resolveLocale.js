// frontend/src/dev-admin/help/resolveLocale.js
//
// Pure logic pulled out of GuideView.jsx so it can be tested with
// `node --test` directly (node cannot parse JSX). A stub payload (no
// sections, no checks) never wins over a real one, so an Icelandic operator
// reading an untranslated guide falls back to the canonical-locale content
// plus a visible notice, never a blank page.

export function resolveLocale(guide, requested) {
  const locales = guide?.locales || {};
  const requestedPayload = locales[requested];
  if (requestedPayload && !requestedPayload.stub) {
    return { locale: requested, isFallback: false };
  }
  return { locale: guide?.canonical_locale, isFallback: true };
}
