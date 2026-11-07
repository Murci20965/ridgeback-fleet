"use client";

import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

// Radix reserves the empty string, so "no filter" needs its own value.
const ALL = "all";

/** A dropdown that matches the app, with keyboard and screen reader support from Radix. */
export function FilterSelect({
  label,
  value,
  allLabel,
  options,
  onChange,
}: {
  label: string;
  value: string | null;
  allLabel: string;
  options: readonly string[];
  onChange: (value: string | null) => void;
}) {
  return (
    <Select.Root
      value={value ?? ALL}
      onValueChange={(next) => onChange(next === ALL ? null : next)}
    >
      <Select.Trigger
        aria-label={label}
        className={`pressable flex h-[42px] cursor-pointer items-center gap-1.5 rounded-[12px] bg-filter pr-2.5 pl-3.5 text-[13px] ${
          value ? "font-medium text-ink" : "text-ink-2"
        } hover:text-ink`}
      >
        <Select.Value />
        <Select.Icon>
          <ChevronDown size={14} className="text-ink-2" aria-hidden />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content position="popper" sideOffset={6} align="start" className="select-menu z-50">
          <Select.Viewport className="p-1.5">
            {[ALL, ...options].map((option) => (
              <Select.Item
                key={option}
                value={option}
                className="flex min-h-9 min-w-40 cursor-pointer items-center justify-between gap-6 rounded-[9px] px-2.5 text-[13px] outline-none select-none data-[highlighted]:bg-surface-2"
              >
                <Select.ItemText>{option === ALL ? allLabel : option}</Select.ItemText>
                <Select.ItemIndicator>
                  <Check size={14} className="text-accent" aria-hidden />
                </Select.ItemIndicator>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
