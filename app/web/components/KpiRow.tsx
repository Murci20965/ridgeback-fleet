import { formatCount, formatHours, fullDay, weekDays } from "@/lib/format";
import type { DailySummary, Kpis } from "@/lib/types";

type Tone = "activity" | "safety";

const BAR_TONE: Record<Tone, { strong: string; soft: string }> = {
  activity: { strong: "bg-activity", soft: "bg-activity-soft" },
  safety: { strong: "bg-safety", soft: "bg-safety-soft" },
};

/** Seven small bars. The selected day stands out, or the peak day in the week view. */
function MiniBars({
  points,
  tone,
  selectedDay,
}: {
  points: { day: string; value: number }[];
  tone: Tone;
  selectedDay: string | null;
}) {
  const highest = Math.max(...points.map((point) => point.value), 0);
  const peak = points.find((point) => point.value === highest)?.day;
  const highlighted = selectedDay ?? peak;

  return (
    <div className="flex h-9 w-full shrink-0 items-end gap-0.5 sm:w-[72px]" aria-hidden>
      {points.map((point) => {
        const height = highest > 0 ? (point.value / highest) * 100 : 0;
        return (
          <div
            key={point.day}
            title={`${fullDay(point.day)}: ${formatCount(point.value)}`}
            className={`min-h-0.5 flex-1 rounded-t-sm transition-[height] duration-300 ease-out motion-reduce:transition-none ${
              point.day === highlighted ? BAR_TONE[tone].strong : BAR_TONE[tone].soft
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
  tone,
  points,
  selectedDay,
}: {
  label: string;
  value: string;
  note: string;
  tone: Tone;
  points: { day: string; value: number }[];
  selectedDay: string | null;
}) {
  return (
    <div className="min-w-0 rounded-2xl border border-line bg-surface p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <dt className="text-[13px] text-ink-2">{label}</dt>
      <dd className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <span className="text-[26px] leading-none font-semibold tracking-tight">{value}</span>
        <MiniBars points={points} tone={tone} selectedDay={selectedDay} />
      </dd>
      <dd className="mt-2 text-xs text-ink-2">{note}</dd>
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
    <dl className="rise grid grid-cols-2 gap-3 xl:grid-cols-4">
      <Tile
        label="Run hours"
        value={formatHours(kpis.run_hours)}
        note="Motor running time"
        tone="activity"
        points={series((row) => row.run_hours)}
        selectedDay={selectedDay}
      />
      <Tile
        label="Active machines"
        value={`${kpis.active_machines} of ${kpis.fleet_size}`}
        note="Ran at least once"
        tone="activity"
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
        tone="safety"
        points={series((row) => row.impacts)}
        selectedDay={selectedDay}
      />
      <Tile
        label="Harsh events"
        value={formatCount(kpis.harsh_events)}
        note="Braking, acceleration, speeding"
        tone="safety"
        points={series((row) => row.harsh_events)}
        selectedDay={selectedDay}
      />
    </dl>
  );
}
