"use client";

import { useState } from "react";
import { Panel, ShowMore } from "@/components/Panel";
import { formatHours } from "@/lib/format";
import type { MachineRow } from "@/lib/types";

const COLLAPSED_ROWS = 8;

function SortButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`pressable min-h-8 rounded-md px-2.5 text-xs ${
        active ? "bg-surface font-medium text-ink shadow-sm" : "text-ink-2 hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

export function MachineHours({ machines, isDay }: { machines: MachineRow[]; isDay: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const [leastFirst, setLeastFirst] = useState(false);
  // The API sends the busiest first. Machines that didn't run lead the least used view.
  const ordered = leastFirst ? [...machines].reverse() : machines;
  const shown = expanded ? ordered : ordered.slice(0, COLLAPSED_ROWS);
  const highest = Math.max(...machines.map((machine) => machine.run_hours), 1);

  return (
    <Panel title="Run hours by machine">
      {machines.length === 0 ? (
        <p className="text-sm text-ink-2">No machines match these filters.</p>
      ) : (
        <>
          <div className="mb-3 inline-flex gap-0.5 rounded-lg bg-surface-2 p-0.5" role="group" aria-label="Sort machines">
            <SortButton active={!leastFirst} onClick={() => setLeastFirst(false)}>
              Most used
            </SortButton>
            <SortButton active={leastFirst} onClick={() => setLeastFirst(true)}>
              Least used
            </SortButton>
          </div>
          <ul className="grid gap-2">
            {shown.map((machine) => (
              <li key={machine.ref_no}>
                <div className="flex items-baseline justify-between gap-3 text-[13px]">
                  <span className="min-w-0 truncate">
                    {machine.ref_no}
                    <span className="ml-2 text-xs text-ink-2">
                      {machine.machine_type} · {machine.assigned_branch}
                    </span>
                  </span>
                  <span className="shrink-0 font-medium tabular-nums">
                    {machine.active ? formatHours(machine.run_hours) : isDay ? "Idle" : "Didn’t run"}
                  </span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-surface-2" aria-hidden>
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${(machine.run_hours / highest) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
          {machines.length > COLLAPSED_ROWS && (
            <ShowMore
              expanded={expanded}
              total={machines.length}
              onClick={() => setExpanded((value) => !value)}
            />
          )}
        </>
      )}
    </Panel>
  );
}
