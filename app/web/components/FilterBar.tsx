"use client";

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
      className={`pressable min-h-9 shrink-0 rounded-lg px-2.5 text-[13px] sm:px-3 ${
        active
          ? "bg-accent font-medium text-on-accent"
          : "text-ink-2 hover:bg-surface-2 disabled:text-muted disabled:opacity-50 disabled:hover:bg-transparent"
      }`}
    >
      {children}
    </button>
  );
}

const selectClass =
  "min-h-9 rounded-lg border border-line bg-surface pl-2.5 pr-1 text-[13px] text-ink hover:border-line-strong";

export function FilterBar({ coverage }: { coverage: Coverage }) {
  const { filters, setFilter } = useFilters();
  const days = weekDays(coverage.week_start);
  const hasData = (day: string) => day >= coverage.first_date && day <= coverage.last_date;

  return (
    <section
      aria-label="Filters"
      className="sticky top-0 z-20 -mx-4 mt-3 flex flex-wrap items-center gap-2 bg-page px-4 py-2 lg:mx-0 lg:px-0"
    >
      <div className="flex max-w-full gap-0.5 overflow-x-auto rounded-xl border border-line bg-surface p-1 [scrollbar-width:none]">
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
      <div className="flex gap-2">
        <select
          aria-label="Branch"
          className={selectClass}
          value={filters.branch ?? ""}
          onChange={(event) => setFilter("branch", event.target.value || null)}
        >
          <option value="">All branches</option>
          {BRANCHES.map((branch) => (
            <option key={branch}>{branch}</option>
          ))}
        </select>
        <select
          aria-label="Machine type"
          className={selectClass}
          value={filters.type ?? ""}
          onChange={(event) => setFilter("type", event.target.value || null)}
        >
          <option value="">All machines</option>
          {MACHINE_TYPES.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
      </div>
    </section>
  );
}
