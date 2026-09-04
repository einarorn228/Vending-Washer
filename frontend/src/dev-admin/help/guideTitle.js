// frontend/src/dev-admin/help/guideTitle.js
//
// Pure logic shared by HelpPanel.jsx and HelpDrawer.jsx: the two surfaces
// independently reimplemented the same fallback chain (requested locale ->
// canonical locale -> guide id), which let them drift. This is the single
// source of truth for both.

export function makeTitleFor(manifest, locale) {
  return (id) => {
    const guide = manifest?.guides?.[id];
    if (!guide) return id;
    const payload = guide.locales?.[locale] || guide.locales?.[guide.canonical_locale];
    return payload?.title || id;
  };
}
