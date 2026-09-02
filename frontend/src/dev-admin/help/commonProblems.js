// frontend/src/dev-admin/help/commonProblems.js
// Derived from guide metadata so the landing rail can never drift from the corpus.
export function commonProblems(manifest, locale) {
  return Object.values(manifest.guides || {})
    .filter((g) => g.kind === 'troubleshooting' && Number.isInteger(g.common_problem_rank))
    .map((g) => {
      const payload = g.locales[locale] || g.locales[manifest.default_locale] || Object.values(g.locales)[0];
      return { guideId: g.id, title: payload?.title || g.id, rank: g.common_problem_rank };
    })
    .sort((a, b) => a.rank - b.rank || a.guideId.localeCompare(b.guideId));
}
