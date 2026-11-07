"use client";

import { useState } from "react";
import { Panel, ShowMore } from "@/components/Panel";
import type { DriverRow } from "@/lib/types";

const COLLAPSED_ROWS = 7;
const cell = "py-1.5 text-right tabular-nums";
const heading = "pb-1.5 text-xs font-normal text-ink-2";

export function DriverTable({ drivers }: { drivers: DriverRow[] }) {
  const [expanded, setExpanded] = useState(false);
  const named = drivers.filter((driver) => driver.driver_name);
  const unattributed = drivers.find((driver) => !driver.driver_name);
  const shown = expanded ? named : named.slice(0, COLLAPSED_ROWS);

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
                <th scope="col" className={`${heading} text-right`}>Impacts</th>
                <th scope="col" className={`${heading} text-right`}>Harsh</th>
                <th scope="col" className={`${heading} text-right`}>Idle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line border-t border-line">
              {shown.map((driver) => (
                <tr key={driver.driver_name}>
                  <th scope="row" className="py-1.5 pr-2 text-left font-normal">
                    {driver.driver_name}
                  </th>
                  <td className={`${cell} font-medium`}>{driver.impacts}</td>
                  <td className={`${cell} pl-3`}>{driver.harsh}</td>
                  <td className={`${cell} pl-3`}>{driver.idle}</td>
                </tr>
              ))}
              {unattributed && (
                <tr className="text-ink-2">
                  <th scope="row" className="py-1.5 pr-2 text-left font-normal">
                    No driver logged on
                  </th>
                  <td className={cell}>{unattributed.impacts}</td>
                  <td className={`${cell} pl-3`}>{unattributed.harsh}</td>
                  <td className={`${cell} pl-3`}>{unattributed.idle}</td>
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
