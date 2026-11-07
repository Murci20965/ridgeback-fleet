"use client";

import { ArrowUpRight } from "lucide-react";
import { useChatBridge } from "@/components/ChatBridge";
import { CountUp } from "@/components/CountUp";
import { useFilters } from "@/components/FilterProvider";
import { formatCount, formatHours } from "@/lib/format";
import { kpiQuestions } from "@/lib/questions";
import type { Kpis } from "@/lib/types";

function Tile({
  label,
  value,
  note,
  question,
}: {
  label: string;
  value: React.ReactNode;
  note: string;
  question: string;
}) {
  const { askChat } = useChatBridge();
  return (
    <div className="card tile group relative min-w-0 p-5">
      <dt className="text-[13px] text-ink-2">{label}</dt>
      <dd className="mt-2 text-[32px] leading-none font-semibold tracking-[-0.022em]">{value}</dd>
      <dd className="mt-3 text-xs text-ink-2">{note}</dd>
      <button
        onClick={() => askChat(question)}
        aria-label={`Ask the assistant: ${question}`}
        title={question}
        className="absolute inset-0 cursor-pointer rounded-[20px]"
      >
        <ArrowUpRight
          size={15}
          className="absolute top-4 right-4 text-ink-2 opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
          aria-hidden
        />
      </button>
    </div>
  );
}

export function KpiRow({ kpis }: { kpis: Kpis }) {
  const { filters } = useFilters();
  const questions = kpiQuestions(filters);

  return (
    <dl className="rise grid grid-cols-2 gap-5 xl:grid-cols-4">
      <Tile
        label="Run hours"
        value={<CountUp value={kpis.run_hours} format={formatHours} />}
        note="Motor running time"
        question={questions.runHours}
      />
      <Tile
        label="Active machines"
        value={
          <>
            <CountUp value={kpis.active_machines} format={formatCount} /> of{" "}
            <CountUp value={kpis.fleet_size} format={formatCount} />
          </>
        }
        note="Ran at least once"
        question={questions.active}
      />
      <Tile
        label="Impacts"
        value={<CountUp value={kpis.impacts} format={formatCount} />}
        note={
          kpis.unattributed_impacts > 0
            ? `${kpis.unattributed_impacts} with no driver logged on`
            : "All have a driver"
        }
        question={questions.impacts}
      />
      <Tile
        label="Harsh events"
        value={<CountUp value={kpis.harsh_events} format={formatCount} />}
        note="Braking, acceleration, speeding"
        question={questions.harsh}
      />
    </dl>
  );
}
