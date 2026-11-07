"use client";

import { X } from "lucide-react";
import { useFilters } from "@/components/FilterProvider";
import { FilterSelect } from "@/components/FilterSelect";
import { Segmented } from "@/components/Segmented";
import { rangeLabel, shortWeekday, weekDays } from "@/lib/format";
import { BRANCHES, MACHINE_TYPES, type Coverage } from "@/lib/types";

const WEEK = "week";

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
      <Segmented
        ariaLabel="Period"
        value={filters.day ?? WEEK}
        onChange={(value) => setFilter("day", value === WEEK ? null : value)}
        options={[
          { value: WEEK, label: "Week" },
          ...days.map((day) => ({
            value: day,
            label: shortWeekday(day),
            ariaLabel: rangeLabel(day, day),
            disabled: !hasData(day),
          })),
        ]}
      />
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
