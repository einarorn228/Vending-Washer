// frontend/src/dev-admin/help/blockDescriptors.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { blockToDescriptor } from './blockDescriptors.js';

test('every allowlisted block maps to a descriptor', () => {
  const kinds = ['paragraph', 'heading', 'ordered_list', 'unordered_list',
                 'code_block', 'table', 'callout'];
  for (const type of kinds) {
    assert.ok(blockToDescriptor({ type, inlines: [], items: [], blocks: [], rows: [], header: [] }),
      `no descriptor for ${type}`);
  }
});

test('an unknown block type renders nothing rather than throwing', () => {
  assert.equal(blockToDescriptor({ type: 'script' }), null);
});

test('setting_ref keeps its identifier verbatim', () => {
  const d = blockToDescriptor({ type: 'paragraph',
    inlines: [{ type: 'setting_ref', value: 'telemetry_enabled' }] });
  assert.equal(d.inlines[0].value, 'telemetry_enabled');
});

test('heading defaults to level 2 and empty text when fields are missing', () => {
  const d = blockToDescriptor({ type: 'heading' });
  assert.equal(d.type, 'heading');
  assert.equal(d.level, 2);
  assert.equal(d.text, '');
});

test('paragraph defaults to an empty inlines array when missing', () => {
  const d = blockToDescriptor({ type: 'paragraph' });
  assert.equal(d.type, 'paragraph');
  assert.deepEqual(d.inlines, []);
});

test('code_block defaults language and text when missing', () => {
  const d = blockToDescriptor({ type: 'code_block' });
  assert.equal(d.type, 'code_block');
  assert.equal(d.language, '');
  assert.equal(d.text, '');
});

test('unordered_list nests item blocks as lists of descriptors', () => {
  const d = blockToDescriptor({
    type: 'unordered_list',
    items: [
      [{ type: 'paragraph', inlines: [{ type: 'text', text: 'first' }] }],
      [{ type: 'paragraph', inlines: [{ type: 'text', text: 'second' }] },
       { type: 'unordered_list', items: [[{ type: 'paragraph', inlines: [] }]] }],
    ],
  });
  assert.equal(d.type, 'unordered_list');
  assert.equal(d.items.length, 2);
  assert.equal(d.items[0].length, 1);
  assert.equal(d.items[0][0].type, 'paragraph');
  assert.equal(d.items[0][0].inlines[0].text, 'first');
  assert.equal(d.items[1].length, 2);
  assert.equal(d.items[1][1].type, 'unordered_list');
  assert.equal(d.items[1][1].items[0][0].type, 'paragraph');
});

test('ordered_list defaults items to an empty array when missing', () => {
  const d = blockToDescriptor({ type: 'ordered_list' });
  assert.equal(d.type, 'ordered_list');
  assert.deepEqual(d.items, []);
});

test('table converts header cells and row cells to inline descriptor lists', () => {
  const d = blockToDescriptor({
    type: 'table',
    header: [[{ type: 'text', text: 'Name' }], [{ type: 'text', text: 'Value' }]],
    rows: [
      [[{ type: 'text', text: 'a' }], [{ type: 'text', text: '1' }]],
      [[{ type: 'text', text: 'b' }], [{ type: 'text', text: '2' }]],
    ],
  });
  assert.equal(d.type, 'table');
  assert.equal(d.header.length, 2);
  assert.equal(d.header[0][0].text, 'Name');
  assert.equal(d.rows.length, 2);
  assert.equal(d.rows[1][1][0].text, '2');
});

test('table defaults header and rows to empty arrays when missing', () => {
  const d = blockToDescriptor({ type: 'table' });
  assert.deepEqual(d.header, []);
  assert.deepEqual(d.rows, []);
});

test('callout defaults level to note and blocks to an empty array', () => {
  const d = blockToDescriptor({ type: 'callout' });
  assert.equal(d.type, 'callout');
  assert.equal(d.level, 'note');
  assert.deepEqual(d.blocks, []);
});

test('callout preserves an explicit warning/danger level and nested blocks', () => {
  const warning = blockToDescriptor({
    type: 'callout',
    level: 'warning',
    blocks: [{ type: 'paragraph', inlines: [{ type: 'text', text: 'careful' }] }],
  });
  assert.equal(warning.level, 'warning');
  assert.equal(warning.blocks[0].inlines[0].text, 'careful');

  const danger = blockToDescriptor({ type: 'callout', level: 'danger', blocks: [] });
  assert.equal(danger.level, 'danger');
});

test('guide_link and external_link inlines keep their fields verbatim', () => {
  const d = blockToDescriptor({
    type: 'paragraph',
    inlines: [
      { type: 'guide_link', guide_id: 'wash-cycle-stuck', text: 'see this guide' },
      { type: 'external_link', url: 'https://example.com/manual', text: 'manual' },
    ],
  });
  assert.equal(d.inlines[0].type, 'guide_link');
  assert.equal(d.inlines[0].guide_id, 'wash-cycle-stuck');
  assert.equal(d.inlines[0].text, 'see this guide');
  assert.equal(d.inlines[1].type, 'external_link');
  assert.equal(d.inlines[1].url, 'https://example.com/manual');
  assert.equal(d.inlines[1].text, 'manual');
});

test('strong and em inlines carry their own nested inline list', () => {
  const d = blockToDescriptor({
    type: 'paragraph',
    inlines: [
      { type: 'strong', inlines: [{ type: 'text', text: 'bold' }] },
      { type: 'em', inlines: [{ type: 'text', text: 'italic' }] },
    ],
  });
  assert.equal(d.inlines[0].type, 'strong');
  assert.equal(d.inlines[0].inlines[0].text, 'bold');
  assert.equal(d.inlines[1].type, 'em');
  assert.equal(d.inlines[1].inlines[0].text, 'italic');
});

test('an unknown inline type is dropped rather than thrown on', () => {
  const d = blockToDescriptor({
    type: 'paragraph',
    inlines: [
      { type: 'text', text: 'kept' },
      { type: 'video', src: 'nope' },
    ],
  });
  assert.equal(d.inlines.length, 1);
  assert.equal(d.inlines[0].text, 'kept');
});
