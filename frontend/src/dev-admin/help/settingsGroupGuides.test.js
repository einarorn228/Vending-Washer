// frontend/src/dev-admin/help/settingsGroupGuides.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SETTINGS_GROUP_GUIDES } from './settingsGroupGuides.js';

const SETTING_GROUP_IDS = [
  'dev_admin', 'api_security', 'scanner', 'machine_timing', 'screen_timing',
  'hardware_timing', 'kiosk', 'runtime', 'codes', 'provider', 'logging',
];

const KEBAB_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

test('every key in the map is one of the eleven setting group ids', () => {
  for (const key of Object.keys(SETTINGS_GROUP_GUIDES)) {
    assert.ok(SETTING_GROUP_IDS.includes(key), `unexpected group id ${key}`);
  }
});

test('every value in the map is a kebab-case guide id', () => {
  for (const value of Object.values(SETTINGS_GROUP_GUIDES)) {
    assert.match(value, KEBAB_RE, `${value} is not kebab-case`);
  }
});
