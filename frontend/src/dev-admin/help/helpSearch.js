// Icelandic inflection is suffixal, so a stable stem sits at the front of the word.
// Folding plus prefix matching absorbs definite forms, plurals, genitives and
// head-initial compounds without a stemmer or any NLP dependency.
// Keep fold() behaviourally identical to backend/help/search_index.py.

const FOLD_MAP = { þ: 'th', ð: 'd', æ: 'ae', ö: 'o' };
export const MIN_TOKEN_LEN = 4;

export const FIELD_WEIGHTS = { title: 100, aliases: 90, summary: 40, headings: 30, body: 8 };
const PREFIX_PENALTY = 0.6;

const STOPWORDS = new Set([
  'og', 'eda', 'sem', 'thad', 'their', 'ekki', 'vera', 'verdur', 'thegar', 'meira',
  'the', 'and', 'for', 'with', 'that', 'this', 'from', 'your', 'should', 'when',
]);

export function fold(text) {
  const lowered = String(text || '').toLowerCase();
  const expanded = Array.from(lowered).map((c) => FOLD_MAP[c] || c).join('');
  return expanded.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

export function tokenise(text) {
  return (fold(text).match(/[a-z0-9]+/g) || []).filter((t) => t.length >= 2);
}

function scoreToken(token, terms) {
  let best = 0;
  for (const term of terms) {
    if (token === term) return 1;
    if (token.length < MIN_TOKEN_LEN || term.length < MIN_TOKEN_LEN) continue;
    if (token.startsWith(term) || term.startsWith(token)) {
      const shorter = Math.min(token.length, term.length);
      const longer = Math.max(token.length, term.length);
      best = Math.max(best, PREFIX_PENALTY * (shorter / longer));
    }
  }
  return best;
}

export function searchGuides(query, manifest, locale) {
  const tokens = tokenise(query).filter((t) => t.length >= MIN_TOKEN_LEN && !STOPWORDS.has(t));
  if (!tokens.length) return [];

  const results = [];
  for (const [guideId, perLocale] of Object.entries(manifest.search || {})) {
    const record = perLocale[locale] || perLocale[manifest.default_locale] || Object.values(perLocale)[0];
    if (!record) continue;
    let score = 0;
    for (const token of tokens) {
      for (const [field, weight] of Object.entries(FIELD_WEIGHTS)) {
        score += weight * scoreToken(token, record[field] || []);
      }
    }
    if (score > 0) results.push({ guideId, score });
  }
  return results.sort((a, b) => b.score - a.score || a.guideId.localeCompare(b.guideId));
}
