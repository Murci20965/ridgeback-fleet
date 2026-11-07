"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useFilters } from "@/components/FilterProvider";
import { Panel } from "@/components/Panel";
import { formatCount, formatHours, fullDay, shortWeekday, weekDays } from "@/lib/format";
import { BRANCHES, type BranchRow, type Coverage, type DailyBranchHours } from "@/lib/types";

// Colour follows the branch, so filtering never repaints a branch.
const BRANCH_COLOUR: Record<string, string> = {
  Airport: "var(--series-1)",
  Harbour: "var(--series-2)",
  Northgate: "var(--series-3)",
  Riverside: "var(--series-4)",
};

interface TooltipProps {
  active?: boolean;
  label?: string;
  payload?: { dataKey?: unknown; value?: unknown }[];
}

function ChartTooltip({ active, label, payload }: TooltipProps) {
  if (!active || !payload?.length || !label) return null;
  const rows = payload.filter((row) => Number(row.value) > 0).reverse();
  const total = rows.reduce((sum, row) => sum + Number(row.value), 0);
  return (
    <div className="rounded-lg border border-line bg-surface p-2.5 text-xs shadow-lg">
      <p className="font-medium">{fullDay(label)}</p>
      <ul className="mt-1 grid gap-0.5">
        {rows.map((row) => (
          <li key={String(row.dataKey)} className="flex items-center gap-1.5 text-ink-2">
            <span
              className="size-2 rounded-sm"
              style={{ background: BRANCH_COLOUR[String(row.dataKey)] }}
              aria-hidden
            />
            <span className="mr-3 flex-1">{String(row.dataKey)}</span>
            <span className="tabular-nums text-ink">{formatHours(Number(row.value))} h</span>
          </li>
        ))}
      </ul>
      <p className="mt-1 border-t border-line pt-1 text-right font-medium tabular-nums">
        {formatHours(total)} h
      </p>
    </div>
  );
}

export function BranchActivity({
  coverage,
  daily,
  branches,
}: {
  coverage: Coverage;
  daily: DailyBranchHours[];
  branches: BranchRow[];
}) {
  const { filters, setFilter } = useFilters();

  const chartData = useMemo(
    () =>
      weekDays(coverage.week_start).map((day) => {
        const row: Record<string, number | string> = { day };
        for (const item of daily) {
          if (item.event_date === day) row[item.branch] = item.run_hours;
        }
        return row;
      }),
    [coverage.week_start, daily],
  );

  const shownBranches = BRANCHES.filter(
    (branch) => !filters.branch || filters.branch === branch,
  );

  // Every shown branch keeps a row, because these rows are also the chart's legend.
  const rows = shownBranches
    .map(
      (branch) =>
        branches.find((row) => row.branch === branch) ?? {
          branch,
          run_hours: 0,
          active_machines: 0,
          impacts: 0,
          harsh: 0,
        },
    )
    .sort((a, b) => b.run_hours - a.run_hours);

  return (
    <Panel title="Branch activity" subtitle="Select a day or a branch to focus on it">
      <div
        className="h-56"
        role="img"
        aria-label="Stacked columns of run hours per day for each branch. The table below has the totals."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: -20 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis
              dataKey="day"
              tickFormatter={shortWeekday}
              tickLine={false}
              axisLine={{ stroke: "var(--line-strong)" }}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
            />
            <Tooltip
              content={<ChartTooltip />}
              cursor={{ fill: "var(--surface-2)" }}
              isAnimationActive={false}
            />
            {shownBranches.map((branch, index) => (
              <Bar
                key={branch}
                dataKey={branch}
                stackId="hours"
                maxBarSize={24}
                fill={BRANCH_COLOUR[branch]}
                stroke="var(--surface)"
                strokeWidth={2}
                radius={index === shownBranches.length - 1 ? [4, 4, 0, 0] : 0}
                animationDuration={320}
                cursor="pointer"
                onClick={(entry: { payload?: { day?: string } }) => {
                  const day = entry.payload?.day;
                  if (day) setFilter("day", filters.day === day ? null : day);
                }}
              >
                {chartData.map((row) => (
                  <Cell
                    key={String(row.day)}
                    fillOpacity={!filters.day || filters.day === row.day ? 1 : 0.3}
                  />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="mt-3 w-full text-[13px]">
        <thead>
          <tr className="text-xs text-ink-2">
            <th scope="col" className="pb-1 text-left font-normal">Branch</th>
            <th scope="col" className="pb-1 text-right font-normal">Hours</th>
            <th scope="col" className="pb-1 text-right font-normal">Machines</th>
            <th scope="col" className="pb-1 text-right font-normal">Impacts</th>
            <th scope="col" className="pb-1 text-right font-normal">Harsh</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line border-t border-line tabular-nums">
          {rows.map((row) => (
            <tr
              key={row.branch}
              onClick={() => setFilter("branch", filters.branch === row.branch ? null : row.branch)}
              className={`cursor-pointer transition-colors duration-150 hover:bg-surface-2 ${
                filters.branch === row.branch ? "bg-surface-2" : ""
              }`}
            >
              <th scope="row" className="rounded-l-lg py-2.5 pl-1 text-left font-normal">
                {/* The row handles the click. This button makes it reachable by keyboard. */}
                <button
                  aria-pressed={filters.branch === row.branch}
                  aria-label={`Filter by ${row.branch}`}
                  className="flex cursor-pointer items-center gap-2"
                >
                  <span
                    className="size-2.5 rounded-full"
                    style={{ background: BRANCH_COLOUR[row.branch] }}
                    aria-hidden
                  />
                  {row.branch}
                </button>
              </th>
              <td className="py-2.5 text-right font-medium">{formatHours(row.run_hours)}</td>
              <td className="py-2.5 text-right">{row.active_machines}</td>
              <td className="py-2.5 text-right">{formatCount(row.impacts)}</td>
              <td className="py-2.5 text-right">{formatCount(row.harsh)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
