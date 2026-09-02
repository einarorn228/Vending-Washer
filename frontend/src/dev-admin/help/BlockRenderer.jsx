// frontend/src/dev-admin/help/BlockRenderer.jsx
//
// Thin consumer of blockDescriptors.js: turns the pure descriptor tree into
// React elements. No HTML strings and no dangerouslySetInnerHTML anywhere in
// this file — that is the entire point of compiling guides into a strict
// block schema instead of shipping Markdown or HTML to the browser.

import React from 'react';
import { blockToDescriptor } from './blockDescriptors.js';

function renderInline(inline, key, onOpenGuide) {
  switch (inline.type) {
    case 'text':
      return inline.text;
    case 'code':
      return <code key={key}>{inline.text}</code>;
    case 'setting_ref':
      return <code key={key}>{inline.value}</code>;
    case 'strong':
      return <strong key={key}>{renderInlines(inline.inlines, onOpenGuide)}</strong>;
    case 'em':
      return <em key={key}>{renderInlines(inline.inlines, onOpenGuide)}</em>;
    case 'guide_link':
      return (
        <button
          key={key}
          type="button"
          className="dev-admin-guide-link"
          onClick={() => onOpenGuide?.(inline.guide_id, null)}
        >
          {inline.text}
        </button>
      );
    case 'external_link':
      return (
        <a key={key} href={inline.url} target="_blank" rel="noopener noreferrer">
          {inline.text}
        </a>
      );
    default:
      return null;
  }
}

function renderInlines(inlines, onOpenGuide) {
  return (inlines || []).map((inline, index) => renderInline(inline, index, onOpenGuide));
}

function renderListItems(items, onOpenGuide) {
  return items.map((item, index) => (
    <li key={index}>
      {item.map((descriptor, blockIndex) => renderDescriptor(descriptor, blockIndex, onOpenGuide))}
    </li>
  ));
}

function renderDescriptor(descriptor, key, onOpenGuide) {
  switch (descriptor.type) {
    case 'paragraph':
      return <p key={key}>{renderInlines(descriptor.inlines, onOpenGuide)}</p>;

    case 'heading': {
      const level = descriptor.level >= 1 && descriptor.level <= 6 ? descriptor.level : 2;
      const HeadingTag = `h${level}`;
      return <HeadingTag key={key}>{descriptor.text}</HeadingTag>;
    }

    case 'code_block':
      return (
        <pre key={key} className="dev-admin-guide-code-block" data-language={descriptor.language || undefined}>
          <code>{descriptor.text}</code>
        </pre>
      );

    case 'ordered_list':
      return <ol key={key}>{renderListItems(descriptor.items, onOpenGuide)}</ol>;

    case 'unordered_list':
      return <ul key={key}>{renderListItems(descriptor.items, onOpenGuide)}</ul>;

    case 'table':
      return (
        <div key={key} className="dev-admin-table-scroll">
          <table className="dev-admin-table">
            <thead>
              <tr>
                {descriptor.header.map((cell, index) => (
                  <th key={index}>{renderInlines(cell, onOpenGuide)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {descriptor.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>{renderInlines(cell, onOpenGuide)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'callout':
      return (
        <div key={key} className={`dev-admin-guide-callout dev-admin-guide-callout--${descriptor.level}`}>
          {descriptor.blocks.map((block, index) => renderDescriptor(block, index, onOpenGuide))}
        </div>
      );

    default:
      return null;
  }
}

export default function BlockRenderer({ blocks, onOpenGuide }) {
  const list = Array.isArray(blocks) ? blocks : [];
  return (
    <>
      {list.map((block, index) => {
        const descriptor = blockToDescriptor(block);
        return descriptor ? renderDescriptor(descriptor, index, onOpenGuide) : null;
      })}
    </>
  );
}
