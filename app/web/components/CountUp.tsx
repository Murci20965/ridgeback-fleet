"use client";

import { useEffect, useRef, useState } from "react";

const DURATION_MS = 420;

/** Rolls a number to its new value. The first render shows the true value straight away, and
    the final frame is always exact, so an in-between figure can't be left on screen. */
export function CountUp({
  value,
  format,
}: {
  value: number;
  format: (value: number) => string;
}) {
  const [shown, setShown] = useState(value);
  const previous = useRef(value);

  useEffect(() => {
    const from = previous.current;
    previous.current = value;
    if (from === value) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(value);
      return;
    }

    const start = performance.now();
    let frame = requestAnimationFrame(function tick(now) {
      const progress = Math.min((now - start) / DURATION_MS, 1);
      const eased = 1 - (1 - progress) ** 3;
      setShown(progress === 1 ? value : from + (value - from) * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return <span className="tabular-nums">{format(shown)}</span>;
}
