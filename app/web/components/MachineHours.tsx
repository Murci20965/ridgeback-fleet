"use client";

import { useState } from "react";
import { useChatBridge } from "@/components/ChatBridge";
import { useFilters } from "@/components/FilterProvider";
import { Panel, ShowMore } from "@/components/Panel";
import { Segmented } from "@/components/Segmented";
import { formatHours } from "@/lib/format";
import { machineQuestion } from "@/lib/questions";
import type { MachineRow } from "@/lib/types";

const COLLAPSED_ROWS = 8;

export function MachineHours({ machines, isDay }: { machines: MachineRow[]; isDay: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const [leastFirst, setLeastFirst] = useState(false);
  const { askChat } = useChatBridge();
  const { filters } = useFilters();
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
          <div className="mb-4">
            <Segmented
              small
              ariaLabel="Sort machines"
              value={leastFirst ? "least" : "most"}
              onChange={(value) => setLeastFirst(value === "least")}
              options={[
                { value: "most", label: "Most used" },
                { value: "least", label: "Least used" },
              ]}
            />
          </div>
          <ul className="-mx-2 grid gap-1">
            {shown.map((machine) => (
              <li key={machine.ref_no}>
                <button
                  onClick={() => askChat(machineQuestion(machine.ref_no, filters))}
                  title={machineQuestion(machine.ref_no, filters)}
                  className="pressable block w-full cursor-pointer rounded-[12px] p-2 text-left hover:bg-surface-2"
                >
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
                <div className="mt-2 h-1 rounded-full bg-surface-2" aria-hidden>
                  <div
                    className="h-full rounded-full bg-accent transition-[width] duration-300 ease-out motion-reduce:transition-none"
                    style={{ width: `${(machine.run_hours / highest) * 100}%` }}
                  />
                </div>
                </button>
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
