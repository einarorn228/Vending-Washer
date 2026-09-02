// frontend/src/dev-admin/help/blockDescriptors.js
//
// Pure conversion from the backend's strict, allowlisted block/inline schema
// (backend/help/blocks.py) into a plain-object descriptor tree that
// BlockRenderer.jsx can switch over without further validation.
//
// blockToDescriptor never throws: an unrecognised block type returns null
// (dropped by the caller), and an unrecognised inline type is dropped from
// its parent's inline list. This is what keeps a manifest the frontend does
// not fully understand yet from crashing the dev-admin panel — the guide
// just renders with fewer blocks than the author wrote.
//
// Missing fields default rather than throw (empty arrays / empty strings /
// heading level 2) because the manifest is trusted but the schema evolves;
// a block skeleton missing a field it usually has should still render.

const KNOWN_INLINE_TYPES = new Set([
  'text', 'code', 'setting_ref', 'strong', 'em', 'guide_link', 'external_link',
]);

export function inlinesToDescriptors(inlines) {
  const list = Array.isArray(inlines) ? inlines : [];
  const out = [];
  for (const inline of list) {
    const descriptor = inlineToDescriptor(inline);
    if (descriptor) out.push(descriptor);
  }
  return out;
}

function inlineToDescriptor(inline) {
  if (!inline || !KNOWN_INLINE_TYPES.has(inline.type)) return null;
  switch (inline.type) {
    case 'text':
      return { type: 'text', text: inline.text || '' };
    case 'code':
      return { type: 'code', text: inline.text || '' };
    case 'setting_ref':
      return { type: 'setting_ref', value: inline.value || '' };
    case 'strong':
      return { type: 'strong', inlines: inlinesToDescriptors(inline.inlines) };
    case 'em':
      return { type: 'em', inlines: inlinesToDescriptors(inline.inlines) };
    case 'guide_link':
      return { type: 'guide_link', guide_id: inline.guide_id || '', text: inline.text || '' };
    case 'external_link':
      return { type: 'external_link', url: inline.url || '', text: inline.text || '' };
    default:
      return null;
  }
}

function itemsToDescriptors(items) {
  const list = Array.isArray(items) ? items : [];
  return list.map((item) => blocksToDescriptors(item));
}

export function blocksToDescriptors(blocks) {
  const list = Array.isArray(blocks) ? blocks : [];
  const out = [];
  for (const block of list) {
    const descriptor = blockToDescriptor(block);
    if (descriptor) out.push(descriptor);
  }
  return out;
}

export function blockToDescriptor(block) {
  if (!block || typeof block !== 'object') return null;

  switch (block.type) {
    case 'paragraph':
      return { type: 'paragraph', inlines: inlinesToDescriptors(block.inlines) };

    case 'heading':
      return {
        type: 'heading',
        level: Number.isInteger(block.level) ? block.level : 2,
        text: block.text || '',
      };

    case 'code_block':
      return {
        type: 'code_block',
        language: block.language || '',
        text: block.text || '',
      };

    case 'ordered_list':
      return { type: 'ordered_list', items: itemsToDescriptors(block.items) };

    case 'unordered_list':
      return { type: 'unordered_list', items: itemsToDescriptors(block.items) };

    case 'table':
      return {
        type: 'table',
        header: (Array.isArray(block.header) ? block.header : []).map((cell) => inlinesToDescriptors(cell)),
        rows: (Array.isArray(block.rows) ? block.rows : []).map(
          (row) => (Array.isArray(row) ? row : []).map((cell) => inlinesToDescriptors(cell)),
        ),
      };

    case 'callout':
      return {
        type: 'callout',
        level: block.level || 'note',
        blocks: blocksToDescriptors(block.blocks),
      };

    default:
      return null;
  }
}
