// frontend/src/dev-admin/help/resolveLocale.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveLocale } from './resolveLocale.js';

const guide = {
  canonical_locale: 'en',
  locales: {
    en: { title: 'English title', stub: false, sections: [] },
    is: { title: 'Icelandic title', stub: false, sections: [] },
    de: { title: 'German stub', stub: true },
  },
};

test('requested locale present and not a stub resolves to itself, no fallback', () => {
  const result = resolveLocale(guide, 'is');
  assert.deepEqual(result, { locale: 'is', isFallback: false });
});

test('requested locale present but a stub falls back to the canonical locale', () => {
  const result = resolveLocale(guide, 'de');
  assert.deepEqual(result, { locale: 'en', isFallback: true });
});

test('requested locale missing from guide.locales falls back to the canonical locale', () => {
  const result = resolveLocale(guide, 'fr');
  assert.deepEqual(result, { locale: 'en', isFallback: true });
});

test('requested locale undefined falls back to the canonical locale', () => {
  const result = resolveLocale(guide, undefined);
  assert.deepEqual(result, { locale: 'en', isFallback: true });
});

test('a guide whose locales lack the canonical entry entirely still returns canonical_locale without throwing', () => {
  const noCanonicalPayload = {
    canonical_locale: 'en',
    locales: {
      is: { title: 'Icelandic only', stub: false, sections: [] },
    },
  };
  const result = resolveLocale(noCanonicalPayload, 'fr');
  assert.deepEqual(result, { locale: 'en', isFallback: true });
});

test('a guide with no locales object at all does not throw', () => {
  const bareGuide = { canonical_locale: 'en' };
  const result = resolveLocale(bareGuide, 'is');
  assert.deepEqual(result, { locale: 'en', isFallback: true });
});
