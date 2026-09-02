// frontend/src/dev-admin/help/checklistState.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { initialCheckState, setCheckResult, toReportChecks, buildSupportReportBody } from './checklistState.js';

const CHECKS = [{ id: 'telemetry-enabled' }, { id: 'current-reading' }];

test('every check starts as not_checked', () => {
  assert.deepEqual(initialCheckState(CHECKS),
    { 'telemetry-enabled': 'not_checked', 'current-reading': 'not_checked' });
});

test('setting a result does not mutate the previous state', () => {
  const before = initialCheckState(CHECKS);
  const after = setCheckResult(before, 'telemetry-enabled', 'problem');
  assert.equal(before['telemetry-enabled'], 'not_checked');
  assert.equal(after['telemetry-enabled'], 'problem');
});

test('invalid results are ignored', () => {
  const state = setCheckResult(initialCheckState(CHECKS), 'telemetry-enabled', 'banana');
  assert.equal(state['telemetry-enabled'], 'not_checked');
});

test('report payload keeps not_checked entries as evidence', () => {
  const state = setCheckResult(initialCheckState(CHECKS), 'current-reading', 'ok');
  assert.deepEqual(toReportChecks(state), [
    { check_id: 'telemetry-enabled', result: 'not_checked' },
    { check_id: 'current-reading', result: 'ok' },
  ]);
});

test('a machine key passed as machineId lands on the machine_id key', () => {
  const body = buildSupportReportBody({
    guideId: 'scanner-not-scanning',
    machineId: 'washer-3',
    checks: [],
    locale: 'is',
  });
  assert.equal(body.machine_id, 'washer-3');
});

test('undefined or null machineId becomes machine_id: null', () => {
  const withUndefined = buildSupportReportBody({ guideId: 'g', checks: [], locale: 'is' });
  const withNull = buildSupportReportBody({ guideId: 'g', machineId: null, checks: [], locale: 'is' });
  assert.equal(withUndefined.machine_id, null);
  assert.equal(withNull.machine_id, null);
});

test('the body never carries locale_shown, groups, or machine_key keys', () => {
  const body = buildSupportReportBody({
    guideId: 'g', machineId: 'm', checks: [{ check_id: 'x', result: 'ok' }], locale: 'en',
  });
  assert.ok(!('locale_shown' in body));
  assert.ok(!('groups' in body));
  assert.ok(!('machine_key' in body));
  assert.deepEqual(Object.keys(body).sort(), ['checks', 'guide_id', 'locale', 'machine_id']);
});
