// frontend/src/dev-admin/help/commonProblems.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commonProblems } from './commonProblems.js';

const MANIFEST = {
  default_locale: 'is',
  guides: {
    b: { id: 'b', kind: 'troubleshooting', common_problem_rank: 2, locales: { is: { title: 'B' } } },
    a: { id: 'a', kind: 'troubleshooting', common_problem_rank: 1, locales: { is: { title: 'A' } } },
    c: { id: 'c', kind: 'concept', common_problem_rank: 1, locales: { is: { title: 'C' } } },
    d: { id: 'd', kind: 'troubleshooting', common_problem_rank: null, locales: { is: { title: 'D' } } },
  },
};

test('only ranked troubleshooting guides appear, in rank order', () => {
  assert.deepEqual(commonProblems(MANIFEST, 'is').map((g) => g.guideId), ['a', 'b']);
});

test('concept guides are excluded even when ranked', () => {
  assert.ok(!commonProblems(MANIFEST, 'is').some((g) => g.guideId === 'c'));
});

test('falls back to another locale title when the requested one is absent', () => {
  const m = { ...MANIFEST, guides: { a: { id: 'a', kind: 'troubleshooting',
    common_problem_rank: 1, locales: { en: { title: 'Only English' } } } } };
  assert.equal(commonProblems(m, 'is')[0].title, 'Only English');
});
