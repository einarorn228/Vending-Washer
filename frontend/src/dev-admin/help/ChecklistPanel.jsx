// frontend/src/dev-admin/help/ChecklistPanel.jsx
//
// Renders one guide's checklist: a question, its supporting `look_for` /
// `expected` hints, and four result buttons per check. When a check is
// marked `problem` and carries a `problem_guide`, a link to that guide is
// shown so the operator can jump straight to the fix. Technical identifiers
// (`route`, `diagnostics`, ids) are never translated — they render verbatim
// or not at all.

import React from 'react';
import { t } from './helpStrings.js';

const RESULT_ORDER = ['ok', 'problem', 'unsure', 'not_checked'];
const RESULT_STRING_KEY = {
  ok: 'resultOk',
  problem: 'resultProblem',
  unsure: 'resultUnsure',
  not_checked: 'resultNotChecked',
};

export default function ChecklistPanel({ checks, state, onSetResult, locale, onOpenGuide, titleFor }) {
  const list = Array.isArray(checks) ? checks : [];
  if (list.length === 0) return null;

  return (
    <section className="dev-admin-guide-checklist">
      {list.map((check) => {
        const result = state?.[check.id] || 'not_checked';
        return (
          <div key={check.id} className="dev-admin-guide-checklist__item">
            <p className="dev-admin-guide-checklist__question">{check.question}</p>
            {check.look_for ? (
              <p className="dev-admin-guide-checklist__hint">{check.look_for}</p>
            ) : null}
            {check.expected ? (
              <p className="dev-admin-guide-checklist__hint">{check.expected}</p>
            ) : null}
            {check.route ? (
              <p className="dev-admin-guide-checklist__route">{check.route}</p>
            ) : null}

            <div className="dev-admin-guide-checklist__actions" role="group">
              {RESULT_ORDER.map((option) => (
                <button
                  key={option}
                  type="button"
                  className="dev-admin-guide-checklist__result"
                  aria-pressed={result === option}
                  onClick={() => onSetResult?.(check.id, option)}
                >
                  {t(locale, RESULT_STRING_KEY[option])}
                </button>
              ))}
            </div>

            {result === 'problem' && check.problem_guide ? (
              <button
                type="button"
                className="dev-admin-guide-link"
                onClick={() => onOpenGuide?.(check.problem_guide, null)}
              >
                {titleFor ? titleFor(check.problem_guide) : check.problem_guide}
              </button>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
