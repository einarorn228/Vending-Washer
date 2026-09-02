import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fold, tokenise, searchGuides } from './helpSearch.js';

// Same fixtures as backend/tests/test_help_search_index.py — parity is required.
test('folding matches the Python compiler', () => {
  assert.equal(fold('Þvottavél'), 'thvottavel');
  assert.equal(fold('þurrkari'), 'thurrkari');
  assert.equal(fold('aðgengilegur'), 'adgengilegur');
  assert.equal(fold('Ræsir'), 'raesir');
  assert.equal(fold('thvottavel'), fold('þvottavel'));
});

test('tokenise strips punctuation', () => {
  assert.deepEqual(tokenise('Þvottavélin virkar ekki!'), ['thvottavelin', 'virkar', 'ekki']);
});

const MANIFEST = {
  guides: {
    'machine-unavailable': { id: 'machine-unavailable', locales: { is: { title: 'Vélin sýnist upptekin' } } },
    'tune-thresholds': { id: 'tune-thresholds', locales: { is: { title: 'Stilla þröskulda' } } },
  },
  search: {
    'machine-unavailable': { is: { title: ['velin', 'synist', 'upptekin'], aliases: ['thvottavel'],
                                   summary: ['laus'], headings: ['fjarmaeling'], body: ['throskuldur'] } },
    'tune-thresholds': { is: { title: ['stilla', 'throskulda'], aliases: [], summary: [],
                               headings: [], body: ['thvottavel'] } },
  },
};

test('inflected Icelandic query matches the stem via prefix', () => {
  const hits = searchGuides('þvottavélin virkar ekki', MANIFEST, 'is');
  assert.equal(hits[0].guideId, 'machine-unavailable');
});

test('title match outranks a body-only match', () => {
  const hits = searchGuides('þröskulda', MANIFEST, 'is');
  assert.equal(hits[0].guideId, 'tune-thresholds');
});

test('tokens shorter than the minimum do not prefix-match', () => {
  assert.deepEqual(searchGuides('vel', MANIFEST, 'is'), []);
});

test('empty query returns nothing', () => {
  assert.deepEqual(searchGuides('   ', MANIFEST, 'is'), []);
});
