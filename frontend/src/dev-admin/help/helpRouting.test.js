// frontend/src/dev-admin/help/helpRouting.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseHelpHash, formatHelpHash } from './helpRouting.js';

const TABS = ['overview', 'remote_control', 'diagnostics', 'settings', 'machines', 'help'];

test('plain tab hashes still work', () => {
  assert.deepEqual(parseHelpHash('#settings', TABS), { tab: 'settings', guideId: null, anchor: null, invalid: false });
});

test('unknown hash falls back to overview', () => {
  assert.deepEqual(parseHelpHash('#nonsense', TABS), { tab: 'overview', guideId: null, anchor: null, invalid: false });
});

test('bare help hash opens the help landing', () => {
  assert.deepEqual(parseHelpHash('#help', TABS), { tab: 'help', guideId: null, anchor: null, invalid: false });
  assert.deepEqual(parseHelpHash('#help/', TABS), { tab: 'help', guideId: null, anchor: null, invalid: false });
});

test('help hash with a guide id is parsed', () => {
  assert.deepEqual(parseHelpHash('#help/machine-unavailable', TABS),
    { tab: 'help', guideId: 'machine-unavailable', anchor: null, invalid: false });
});

test('help hash with a guide id and anchor is parsed', () => {
  assert.deepEqual(parseHelpHash('#help/machine-unavailable/check-telemetry', TABS),
    { tab: 'help', guideId: 'machine-unavailable', anchor: 'check-telemetry', invalid: false });
});

test('malformed guide ids are rejected rather than passed through', () => {
  assert.deepEqual(parseHelpHash('#help/../../etc/passwd', TABS),
    { tab: 'help', guideId: null, anchor: null, invalid: true });
  assert.deepEqual(parseHelpHash('#help/Not Valid', TABS),
    { tab: 'help', guideId: null, anchor: null, invalid: true });
});

test('a malformed anchor or extra segments mark the route invalid', () => {
  assert.deepEqual(parseHelpHash('#help/machine-unavailable/Bad Anchor', TABS),
    { tab: 'help', guideId: 'machine-unavailable', anchor: null, invalid: true });
  assert.deepEqual(parseHelpHash('#help/machine-unavailable/check-telemetry/extra', TABS),
    { tab: 'help', guideId: 'machine-unavailable', anchor: 'check-telemetry', invalid: true });
});

test('non-string and empty input fall back to overview', () => {
  assert.deepEqual(parseHelpHash(undefined, TABS), { tab: 'overview', guideId: null, anchor: null, invalid: false });
  assert.deepEqual(parseHelpHash('', TABS), { tab: 'overview', guideId: null, anchor: null, invalid: false });
});

test('formatHelpHash round-trips', () => {
  assert.equal(formatHelpHash('machine-unavailable', null), '#help/machine-unavailable');
  assert.equal(formatHelpHash('machine-unavailable', 'check-telemetry'),
    '#help/machine-unavailable/check-telemetry');
});
