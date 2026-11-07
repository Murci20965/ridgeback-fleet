"use client";

import { useLayoutEffect, useRef, useState } from "react";

export interface SegmentOption {
  value: string;
  label: string;
  ariaLabel?: string;
  disabled?: boolean;
}

/** An Apple-style segmented control. A single pill slides to the selected option, and the
    left and right arrow keys move between options. */
export function Segmented({
  options,
  value,
  onChange,
  ariaLabel,
  small = false,
}: {
  options: SegmentOption[];
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
  small?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pill, setPill] = useState<{ left: number; width: number } | null>(null);
  const hasMeasured = useRef(false);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    function measure() {
      const active = container?.querySelector<HTMLElement>('[aria-pressed="true"]');
      if (active) setPill({ left: active.offsetLeft, width: active.offsetWidth });
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, [value]);

  useLayoutEffect(() => {
    // The first position is set without sliding, and only later changes animate.
    if (pill) hasMeasured.current = true;
  }, [pill]);

  function move(from: number, step: number) {
    let next = from + step;
    while (options[next]?.disabled) next += step;
    const option = options[next];
    if (!option) return;
    onChange(option.value);
    const buttons = containerRef.current?.querySelectorAll("button");
    buttons?.[next]?.focus();
    buttons?.[next]?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }

  return (
    <div
      ref={containerRef}
      role="group"
      aria-label={ariaLabel}
      className={`relative flex max-w-full gap-0.5 overflow-x-auto [scrollbar-width:none] ${
        small ? "w-fit rounded-[9px] bg-surface-2 p-[3px]" : "rounded-[12px] bg-filter p-[5px]"
      }`}
    >
      {pill && (
        <span
          aria-hidden
          className={`absolute bg-surface shadow-[0_1px_3px_rgba(0,0,0,0.14)] ${
            small ? "top-[3px] bottom-[3px] rounded-[7px]" : "top-[5px] bottom-[5px] rounded-[9px]"
          } ${
            hasMeasured.current
              ? "transition-[transform,width] duration-[260ms] ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none"
              : ""
          }`}
          style={{ left: 0, width: pill.width, transform: `translateX(${pill.left}px)` }}
        />
      )}
      {options.map((option, index) => {
        const isActive = option.value === value;
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                event.preventDefault();
                move(index, event.key === "ArrowRight" ? 1 : -1);
              }
            }}
            disabled={option.disabled}
            aria-pressed={isActive}
            aria-label={option.ariaLabel}
            className={`pressable relative shrink-0 ${
              small ? "min-h-7 rounded-[7px] px-3 text-xs" : "min-h-8 rounded-[9px] px-2.5 text-[13px] sm:px-3.5"
            } ${
              isActive
                ? "font-medium text-ink"
                : "text-ink-2 hover:text-ink disabled:opacity-40 disabled:hover:text-ink-2"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
