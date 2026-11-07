import { formatCount, formatHours, fullDay, weekDays } from "@/lib/format";
import type { DailySummary, Kpis } from "@/lib/types";

/** Seven small bars. The selected day takes the accent, or the peak day in the week view. */
function MiniBars({
  points,
  selectedDay,
}: {
  points: { day: string; value: number }[];
  selectedDay: string | null;
}) {
  const highest = Math.max(...points.map((point) => point.value), 0);
  const peak = points.find((point) => point.value === highest)?.day;
  const highlighted = selectedDay ?? peak;

  return (
    <div className="flex h-8 w-full shrink-0 items-end gap-[3px] sm:w-[70px]" aria-hidden>
      {points.map((point) => {
        const height = highest > 0 ? (point.value / highest) * 100 : 0;
        return (
          <div
            key={point.day}
            title={`${fullDay(point.day)}: ${formatCount(point.value)}`}
            className={`min-h-0.5 flex-1 rounded-[2px] transition-[height] duration-300 ease-out motion-reduce:transition-none ${
              point.day === highlighted ? "bg-accent" : "bg-bar-soft"
            }`}
            style={{ height: `${Math.max(height, 4)}%` }}
          />
        );
      })}
    </div>
  );
}

function Tile({
  label,
  value,
  note,
  points,
  selectedDay,
}: {
  label: string;
  value: string;
  note: string;
  points: { day: string; value: number }[];
  selectedDay: string | null;
}) {
  return (
    <div className="card min-w-0 p-5">
      <dt className="text-[13px] text-ink-2">{label}</dt>
      <dd className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <span className="text-[28px] leading-none font-semibold tracking-[-0.022em]">{value}</span>
        <MiniBars points={points} selectedDay={selectedDay} />
      </dd>
      <dd className="mt-3 text-xs text-ink-2">{note}</dd>
    </div>
  );
}

export function KpiRow({
  kpis,
  daily,
  weekStart,
  selectedDay,
}: {
  kpis: Kpis;
  daily: DailySummary[];
  weekStart: string;
  selectedDay: string | null;
}) {
  const series = (pick: (row: DailySummary) => number) =>
    weekDays(weekStart).map((day) => {
      const row = daily.find((item) => item.event_date === day);
      return { day, value: row ? pick(row) : 0 };
    });

  return (
    <dl className="rise grid grid-cols-2 gap-5 xl:grid-cols-4">
      <Tile
        label="Run hours"
        value={formatHours(kpis.run_hours)}
        note="Motor running time"
        points={series((row) => row.run_hours)}
        selectedDay={selectedDay}
      />
      <Tile
        label="Active machines"
        value={`${kpis.active_machines} of ${kpis.fleet_size}`}
        note="Ran at least once"
        points={series((row) => row.active_machines)}
        selectedDay={selectedDay}
      />
      <Tile
        label="Impacts"
        value={formatCount(kpis.impacts)}
        note={
          kpis.unattributed_impacts > 0
            ? `${kpis.unattributed_impacts} with no driver logged on`
            : "All have a driver"
        }
        points={series((row) => row.impacts)}
        selectedDay={selectedDay}
      />
      <Tile
        label="Harsh events"
        value={formatCount(kpis.harsh_events)}
        note="Braking, acceleration, speeding"
        points={series((row) => row.harsh_events)}
        selectedDay={selectedDay}
      />
    </dl>
  );
}
