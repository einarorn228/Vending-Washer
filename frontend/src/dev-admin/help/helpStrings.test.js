// frontend/src/dev-admin/help/helpStrings.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { t } from './helpStrings.js';

// Five of the six ContextualHelpLink callsites resolve their accessible name
// through one of these fixed keys (see ContextualHelpLink.jsx); the sixth,
// in SettingsPanel.jsx, uses labelSuffix and only needs the generic "help"
// key below. Pin them so a future edit can't silently drop a locale and
// regress back to an English-only accessible name in the Icelandic panel.
const HELP_LINK_KEYS = [
  'helpRestartRequired',
  'helpSwitchBackOn',
  'helpReisaIntegration',
  'helpTuneThresholds',
  'helpTechnicalMapping',
];

test('every ContextualHelpLink label key resolves to a real string in both locales', () => {
  for (const key of HELP_LINK_KEYS) {
    for (const locale of ['is', 'en']) {
      const value = t(locale, key);
      assert.notEqual(value, key, `${key} has no ${locale} translation and fell back to the raw key`);
      assert.ok(value.length > 0);
    }
  }
});

test('the is and en strings for a given key are actually different', () => {
  // A crude guard against a copy-paste that left the Icelandic value in
  // English: every current key is a full sentence-ish label, so identical
  // is/en text almost certainly means the translation is missing.
  for (const key of HELP_LINK_KEYS) {
    assert.notEqual(t('is', key), t('en', key), `${key} has identical is/en text`);
  }
});

test('the generic "help" fallback used when no label/labelKey/labelSuffix is given', () => {
  assert.equal(t('en', 'help'), 'Help');
  assert.equal(t('is', 'help'), 'Hjálp');
});
