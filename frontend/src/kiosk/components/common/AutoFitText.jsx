import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';

const useIsomorphicLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect;

export default function AutoFitText({ as: Component = 'span', className, children, minScale = 0.72, maxScale = 1, style, ...rest }) {
  const rootRef = useRef(null);
  const measureRef = useRef(null);
  const frameRef = useRef(null);
  const observerRef = useRef(null);
  const [scale, setScale] = useState(maxScale);

  useIsomorphicLayoutEffect(() => {
    const rootElement = rootRef.current;
    const measureElement = measureRef.current;
    if (!rootElement || !measureElement || typeof window === 'undefined') {
      return undefined;
    }

    const clampScale = (value) => Math.max(minScale, Math.min(maxScale, value));

    const recalculateScale = () => {
      const availableWidth = rootElement.clientWidth;
      if (!availableWidth) {
        setScale(maxScale);
        return;
      }

      measureElement.style.fontSize = 'calc(var(--machine-card-title-size) * 1)';
      const fullWidth = measureElement.scrollWidth;
      if (!fullWidth) {
        setScale(maxScale);
        return;
      }

      const nextScale = clampScale(availableWidth / fullWidth);
      setScale((prevScale) => (Math.abs(prevScale - nextScale) > 0.01 ? nextScale : prevScale));
    };

    const queueRecalculate = () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
      frameRef.current = requestAnimationFrame(recalculateScale);
    };

    queueRecalculate();

    observerRef.current = new ResizeObserver(queueRecalculate);
    observerRef.current.observe(rootElement);

    return () => {
      observerRef.current?.disconnect();
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [children, maxScale, minScale]);

  return (
    <Component ref={rootRef} className={className} style={{ ...style, '--auto-fit-scale': scale }} {...rest}>
      <span className="auto-fit-text__measure" ref={measureRef} aria-hidden="true">
        {children}
      </span>
      <span className="auto-fit-text__visible">{children}</span>
    </Component>
  );
}
