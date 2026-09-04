// frontend/src/dev-admin/help/settingsGroupGuides.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SETTINGS_GROUP_GUIDES } from './settingsGroupGuides.js';

const SETTING_GROUP_IDS = [
  'dev_admin', 'api_security', 'scanner', 'machine_timing', 'screen_timing',
  'hardware_timing', 'kiosk', 'runtime', 'codes', 'provider', 'logging',
];

// The whole first-beta corpus. A group may only point at a guide that exists,
// because a Help icon that opens nothing is worse than no Help icon at all.
const CORPUS_GUIDE_IDS = [
  'machine-unavailable', 'machine-does-not-start',
  'all-machines-available-telemetry-stale', 'code-rejected',
  'scanner-not-scanning', 'kiosk-cannot-reach-backend',
  'tune-thresholds', 'no-telemetry-reading', 'reisa-configuration',
  'machine-technical-mapping', 'wrong-machine-starts', 'admin-access-recovery',
  'settings-requiring-restart', 'using-diagnostics', 'admin-panel-orientation',
];

const KEBAB_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

// The map as ruled at the Task 17 checkpoint. Asserted whole rather than by
// shape alone: a silent retarget is exactly the drift this map exists to catch.
const EXPECTED_MAP = {
  dev_admin: 'admin-access-recovery',
  api_security: 'admin-access-recovery',
  scanner: 'scanner-not-scanning',
  machine_timing: 'machine-does-not-start',
  screen_timing: 'admin-panel-orientation',
  hardware_timing: 'machine-does-not-start',
  kiosk: 'admin-panel-orientation',
  runtime: 'admin-panel-orientation',
  codes: 'code-rejected',
  provider: 'reisa-configuration',
  logging: 'settings-requiring-restart',
};

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

test('every target exists in the guide corpus', () => {
  for (const [group, value] of Object.entries(SETTINGS_GROUP_GUIDES)) {
    assert.ok(
      CORPUS_GUIDE_IDS.includes(value),
      `${group} points at ${value}, which is not a corpus guide id`,
    );
  }
});

test('the map is exactly the one ruled at the Task 17 checkpoint', () => {
  assert.deepEqual(SETTINGS_GROUP_GUIDES, EXPECTED_MAP);
});

test('the runtime group points at the guide that discusses its toggles', () => {
  // Retargeted away from settings-requiring-restart: none of
  // backend_relay_enabled / telemetry_enabled / button_box_enabled is
  // restart-required, so that guide would have been a misleading link.
  assert.equal(SETTINGS_GROUP_GUIDES.runtime, 'admin-panel-orientation');
});

test('the logging group points at the guide that names log_level', () => {
  assert.equal(SETTINGS_GROUP_GUIDES.logging, 'settings-requiring-restart');
});
