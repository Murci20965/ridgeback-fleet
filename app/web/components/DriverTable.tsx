"use client";

import { useState } from "react";
import { useChatBridge } from "@/components/ChatBridge";
import { useFilters } from "@/components/FilterProvider";
import { Panel, ShowMore } from "@/components/Panel";
import { driverQuestion } from "@/lib/questions";
import type { DriverRow } from "@/lib/types";

const COLLAPSED_ROWS = 7;
const cell = "py-2.5 pl-3 text-right tabular-nums";
const heading = "pb-1.5 text-xs font-normal text-ink-2";

function ImpactCell({ value, highest, muted }: { value: number; highest: number; muted?: boolean }) {
  return (
    <td className="w-[45%] py-2.5 pl-2">
      <div className="flex items-center justify-end gap-2">
        <div className="h-1 min-w-0 flex-1 rounded-full bg-surface-2" aria-hidden>
          <div
            className={`h-full rounded-full transition-[width] duration-300 ease-out motion-reduce:transition-none ${
              muted ? "bg-line-strong" : "bg-accent"
            }`}
            style={{ width: `${highest > 0 ? (value / highest) * 100 : 0}%` }}
          />
        </div>
        <span className="w-5 text-right font-medium tabular-nums">{value}</span>
      </div>
    </td>
  );
}

export function DriverTable({ drivers }: { drivers: DriverRow[] }) {
  const [expanded, setExpanded] = useState(false);
  const { askChat } = useChatBridge();
  const { filters } = useFilters();
  const named = drivers.filter((driver) => driver.driver_name);
  const unattributed = drivers.find((driver) => !driver.driver_name);
  const shown = expanded ? named : named.slice(0, COLLAPSED_ROWS);
  const highest = Math.max(...drivers.map((driver) => driver.impacts), 0);

  return (
    <Panel title="Drivers by impacts" subtitle="Harsh is braking, acceleration and speeding">
      {drivers.length === 0 ? (
        <p className="text-sm text-ink-2">No driver events for this view.</p>
      ) : (
        <>
          <table className="w-full text-[13px]">
            <thead>
              <tr>
                <th scope="col" className={`${heading} text-left`}>Driver</th>
                <th scope="col" className={`${heading} pl-3 text-right`}>Impacts</th>
                <th scope="col" className={`${heading} pl-3 text-right`}>Harsh</th>
                <th scope="col" className={`${heading} pl-3 text-right`}>Idle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line border-t border-line">
              {shown.map((driver) => (
                <tr
                  key={driver.driver_name}
                  onClick={() => askChat(driverQuestion(driver.driver_name!, filters))}
                  className="cursor-pointer transition-colors duration-150 hover:bg-surface-2"
                >
                  <th scope="row" className="rounded-l-lg py-2.5 pr-2 pl-1 text-left font-normal">
                    {/* The row handles the click. This button makes it reachable by keyboard. */}
                    <button
                      title={driverQuestion(driver.driver_name!, filters)}
                      aria-label={`Ask the assistant: ${driverQuestion(driver.driver_name!, filters)}`}
                      className="cursor-pointer text-left"
                    >
                      {driver.driver_name}
                    </button>
                  </th>
                  <ImpactCell value={driver.impacts} highest={highest} />
                  <td className={cell}>{driver.harsh}</td>
                  <td className={cell}>{driver.idle}</td>
                </tr>
              ))}
              {unattributed && (
                <tr className="text-ink-2">
                  <th scope="row" className="py-2.5 pr-2 text-left font-normal">
                    No driver logged on
                  </th>
                  <ImpactCell value={unattributed.impacts} highest={highest} muted />
                  <td className={cell}>{unattributed.harsh}</td>
                  <td className={cell}>{unattributed.idle}</td>
                </tr>
              )}
            </tbody>
          </table>
          {named.length > COLLAPSED_ROWS && (
            <ShowMore
              expanded={expanded}
              total={named.length}
              onClick={() => setExpanded((value) => !value)}
            />
          )}
        </>
      )}
    </Panel>
  );
}
