"use client";

import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import { useChatBridge } from "@/components/ChatBridge";
import { Panel } from "@/components/Panel";
import type { AttentionItem } from "@/lib/types";

function AskButton({ item, onAsk }: { item: AttentionItem; onAsk: (question: string) => void }) {
  const isCritical = item.severity === "critical";
  return (
    <button
      onClick={() => onAsk(item.question)}
      aria-label={`Ask the assistant: ${item.question}`}
      title={item.question}
      className={`pressable min-h-8 shrink-0 rounded-lg px-2 text-[13px] font-medium ${
        isCritical
          ? "text-critical-ink underline underline-offset-2 hover:bg-black/5"
          : "text-accent-ink hover:bg-accent-wash"
      }`}
    >
      Ask
    </button>
  );
}

export function AttentionList({ items }: { items: AttentionItem[] }) {
  const { askChat } = useChatBridge();
  const critical = items.filter((item) => item.severity === "critical");
  const warnings = items.filter((item) => item.severity === "warning");

  return (
    <Panel
      title="Needs attention"
      subtitle="What to look at first this morning"
      aside={
        critical.length > 0 && (
          <span className="shrink-0 rounded-full bg-critical-wash px-2 py-0.5 text-xs font-medium text-critical-ink">
            {critical.length} critical
          </span>
        )
      }
    >
      {items.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-ink-2">
          <CircleCheck size={16} className="text-good" aria-hidden />
          Nothing needs attention for this view.
        </p>
      ) : (
        <>
          {critical.length > 0 && (
            <ul className="mb-1.5 grid gap-1.5">
              {critical.map((item) => (
                <li
                  key={`${item.kind}-${item.title}`}
                  className="flex items-start gap-2.5 rounded-xl bg-critical-wash p-2.5 text-critical-ink"
                >
                  <CircleAlert size={16} className="mt-0.5 shrink-0" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium break-words">
                      <span className="sr-only">Critical: </span>
                      {item.title}
                    </p>
                    <p className="text-xs">{item.detail}</p>
                  </div>
                  <AskButton item={item} onAsk={askChat} />
                </li>
              ))}
            </ul>
          )}
          <ul className="divide-y divide-line">
            {warnings.map((item) => (
              <li key={`${item.kind}-${item.title}`} className="flex items-start gap-2.5 px-2.5 py-2">
                <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium break-words">
                    <span className="sr-only">Check: </span>
                    {item.title}
                  </p>
                  <p className="text-xs text-ink-2">{item.detail}</p>
                </div>
                <AskButton item={item} onAsk={askChat} />
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
