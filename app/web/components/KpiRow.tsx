import { formatCount, formatHours } from "@/lib/format";
import type { Kpis } from "@/lib/types";

function Tile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3.5">
      <dt className="text-[13px] text-ink-2">{label}</dt>
      <dd className="mt-0.5 text-2xl font-semibold tracking-tight">{value}</dd>
      <dd className="mt-0.5 text-xs text-ink-2">{note}</dd>
    </div>
  );
}

export function KpiRow({ kpis }: { kpis: Kpis }) {
  return (
    <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Tile
        label="Run hours"
        value={formatHours(kpis.run_hours)}
        note="Motor running time"
      />
      <Tile
        label="Active machines"
        value={`${kpis.active_machines} of ${kpis.fleet_size}`}
        note="Ran at least once"
      />
      <Tile
        label="Impacts"
        value={formatCount(kpis.impacts)}
        note={
          kpis.unattributed_impacts > 0
            ? `${kpis.unattributed_impacts} with no driver logged on`
            : "All have a driver"
        }
      />
      <Tile
        label="Harsh events"
        value={formatCount(kpis.harsh_events)}
        note="Braking, acceleration, speeding"
      />
    </dl>
  );
}
