"use client";

import { ChevronDown, X } from "lucide-react";
import { useFilters } from "@/components/FilterProvider";
import { rangeLabel, shortWeekday, weekDays } from "@/lib/format";
import { BRANCHES, MACHINE_TYPES, type Coverage } from "@/lib/types";

function Pill({
  active,
  disabled,
  label,
  onClick,
  children,
}: {
  active: boolean;
  disabled?: boolean;
  label?: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      aria-label={label}
      className={`pressable min-h-8 shrink-0 rounded-[9px] px-2.5 text-[13px] sm:px-3.5 ${
        active
          ? "bg-surface font-medium text-ink shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
          : "text-ink-2 hover:text-ink disabled:opacity-40 disabled:hover:text-ink-2"
      }`}
    >
      {children}
    </button>
  );
}

function FilterSelect({
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
    <div className="relative">
      <select
        aria-label={label}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value || null)}
        className={`h-[42px] cursor-pointer appearance-none rounded-[12px] bg-surface-2 pr-8 pl-3.5 text-[13px] ${
          value ? "font-medium text-ink" : "text-ink-2"
        }`}
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-ink-2"
        aria-hidden
      />
    </div>
  );
}

export function FilterBar({ coverage }: { coverage: Coverage }) {
  const { filters, setFilter, clearFilters } = useFilters();
  const hasFilters = Boolean(filters.day || filters.branch || filters.type);
  const days = weekDays(coverage.week_start);
  const hasData = (day: string) => day >= coverage.first_date && day <= coverage.last_date;

  return (
    <section
      aria-label="Filters"
      className="-mx-4 flex flex-wrap items-center gap-2 bg-page px-4 pt-1 pb-4 lg:sticky lg:top-0 lg:z-20 lg:mx-0 lg:px-0 lg:pt-3"
    >
      <div className="flex max-w-full gap-0.5 overflow-x-auto rounded-[12px] bg-surface-2 p-[5px] [scrollbar-width:none]">
        <Pill active={!filters.day} onClick={() => setFilter("day", null)}>
          Week
        </Pill>
        {days.map((day) => (
          <Pill
            key={day}
            active={filters.day === day}
            disabled={!hasData(day)}
            label={rangeLabel(day, day)}
            onClick={() => setFilter("day", day)}
          >
            {shortWeekday(day)}
          </Pill>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect
          label="Branch"
          value={filters.branch}
          allLabel="All branches"
          options={BRANCHES}
          onChange={(value) => setFilter("branch", value)}
        />
        <FilterSelect
          label="Machine type"
          value={filters.type}
          allLabel="All machines"
          options={MACHINE_TYPES}
          onChange={(value) => setFilter("type", value)}
        />
        {hasFilters && (
          <button
            onClick={clearFilters}
            className="pressable flex min-h-9 items-center gap-1 px-1.5 text-[13px] text-accent-ink hover:underline"
          >
            <X size={14} aria-hidden />
            Clear
          </button>
        )}
      </div>
    </section>
  );
}
