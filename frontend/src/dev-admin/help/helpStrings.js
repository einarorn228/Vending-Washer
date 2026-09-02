// frontend/src/dev-admin/help/helpStrings.js
//
// The only UI chrome for the Help Hub. Guide content itself is never
// translated here — it comes from the manifest's own per-locale payloads.
// Technical identifiers (setting keys, guide ids, anchors) are rendered
// verbatim by the components that consume them and never pass through t().

export const STRINGS = {
  is: {
    help: 'Hjálp',
    guides: 'Leiðbeiningar',
    commonProblems: 'Algeng vandamál',
    searchPlaceholder: 'Leita í leiðbeiningum',
    relatedGuides: 'Tengdar leiðbeiningar',
    copyReport: 'Afrita bilanaupplýsingar',
    reportCopied: 'Afritað',
    resultOk: 'Í lagi',
    resultProblem: 'Vandamál fannst',
    resultUnsure: 'Ekki viss',
    resultNotChecked: 'Ekki athugað',
    fallbackNotice: 'Þessi leiðbeining er ekki enn til á íslensku — sýni enska útgáfu.',
    notFound: 'Leiðbeiningin fannst ekki.',
    unavailable: 'Hjálparefni er ekki tiltækt.',
    noResults: 'Ekkert fannst.',
    riskHigh: 'Mikil áhætta',
  },
  en: {
    help: 'Help',
    guides: 'Guides',
    commonProblems: 'Common problems',
    searchPlaceholder: 'Search guides',
    relatedGuides: 'Related guides',
    copyReport: 'Copy support report',
    reportCopied: 'Copied',
    resultOk: 'OK',
    resultProblem: 'Problem found',
    resultUnsure: 'Not sure',
    resultNotChecked: 'Not checked',
    fallbackNotice: 'This guide is not translated yet — showing the English version.',
    notFound: 'Guide not found.',
    unavailable: 'Help content is unavailable.',
    noResults: 'No results.',
    riskHigh: 'High risk',
  },
};

export function t(locale, key) {
  return STRINGS[locale]?.[key] ?? STRINGS.en[key] ?? key;
}
