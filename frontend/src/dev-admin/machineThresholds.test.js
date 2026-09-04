import test from 'node:test';
import assert from 'node:assert/strict';

import { validateThresholdPair } from './machineThresholds.js';

const KEY = 'technical.off_threshold';

test('a proper hysteresis band passes', () => {
  assert.equal(validateThresholdPair({ on_threshold: 8, off_threshold: 3 }), null);
});

test('equal thresholds are rejected: the mid band would be empty', () => {
  const errors = validateThresholdPair({ on_threshold: 5, off_threshold: 5 });
  assert.ok(errors && errors[KEY]);
});

test('inverted thresholds are rejected', () => {
  const errors = validateThresholdPair({ on_threshold: 3, off_threshold: 9 });
  assert.ok(errors && errors[KEY]);
});

test('the error key matches what the drawer err() helper looks up', () => {
  // The drawer reads errors['technical.<field>'] first, exactly as the API returns it,
  // so a client-side rejection renders in the same place as a server-side one.
  const errors = validateThresholdPair({ on_threshold: 1, off_threshold: 2 });
  assert.deepEqual(Object.keys(errors), [KEY]);
});

test('number inputs hand back strings and must still be compared numerically', () => {
  // '10' > '9' is false as a string comparison; this would silently pass unguarded.
  assert.ok(validateThresholdPair({ on_threshold: '9', off_threshold: '10' }));
  assert.equal(validateThresholdPair({ on_threshold: '10', off_threshold: '9' }), null);
});

test('blank or unparseable values are left to the range check', () => {
  assert.equal(validateThresholdPair({ on_threshold: '', off_threshold: 3 }), null);
  assert.equal(validateThresholdPair({ on_threshold: 8, off_threshold: 'abc' }), null);
  assert.equal(validateThresholdPair(undefined), null);
});
