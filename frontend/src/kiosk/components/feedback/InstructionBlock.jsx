import React from 'react';

export default function InstructionBlock({ title, description }) {
  if (!title && !description) {
    return null;
  }

  return (
    <section className="instruction-block" aria-live="polite">
      {title ? <h2 className="instruction-block__title">{title}</h2> : null}
      {description ? <p className="instruction-block__description">{description}</p> : null}
    </section>
  );
}
