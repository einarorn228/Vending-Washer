// frontend/src/dev-admin/help/checklistState.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { initialCheckState, setCheckResult, toReportChecks } from './checklistState.js';

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
