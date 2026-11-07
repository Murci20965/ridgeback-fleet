"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from "recharts";
import { ResponsiveContainer } from "recharts";
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

  return (
    <Panel
      title="Branch activity"
      subtitle="Run hours per day. Select a day to focus on it."
      className="xl:col-span-1"
    >
      {shownBranches.length > 1 && (
        <ul className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-2" aria-label="Legend">
          {shownBranches.map((branch) => (
            <li key={branch} className="flex items-center gap-1.5">
              <span
                className="size-2.5 rounded-sm"
                style={{ background: BRANCH_COLOUR[branch] }}
                aria-hidden
              />
              {branch}
            </li>
          ))}
        </ul>
      )}
      <div
        className="h-48"
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
                strokeWidth={1}
                radius={index === shownBranches.length - 1 ? [4, 4, 0, 0] : 0}
                isAnimationActive={false}
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
          {branches.map((row) => (
            <tr key={row.branch}>
              <th scope="row" className="py-1.5 text-left font-normal">{row.branch}</th>
              <td className="py-1.5 text-right">{formatHours(row.run_hours)}</td>
              <td className="py-1.5 text-right">{row.active_machines}</td>
              <td className="py-1.5 text-right">{formatCount(row.impacts)}</td>
              <td className="py-1.5 text-right">{formatCount(row.harsh)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {branches.length === 0 && (
        <p className="mt-2 text-sm text-ink-2">No branch activity for this view.</p>
      )}
    </Panel>
  );
}
