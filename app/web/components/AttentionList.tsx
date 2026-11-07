"use client";

import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import { useChatBridge } from "@/components/ChatBridge";
import { Panel } from "@/components/Panel";
import type { AttentionItem } from "@/lib/types";

export function AttentionList({ items }: { items: AttentionItem[] }) {
  const { askChat } = useChatBridge();
  const criticalCount = items.filter((item) => item.severity === "critical").length;

  return (
    <Panel
      title="Needs attention"
      subtitle="What to look at first this morning"
      aside={
        criticalCount > 0 && (
          <span className="shrink-0 pt-1 text-xs font-medium text-critical">
            {criticalCount} critical
          </span>
        )
      }
    >
      {items.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-ink-2">
          <CircleCheck size={16} aria-hidden />
          Nothing needs attention for this view.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => {
            const isCritical = item.severity === "critical";
            const Icon = isCritical ? CircleAlert : TriangleAlert;
            return (
              <li
                key={`${item.kind}-${item.title}`}
                className="flex items-start gap-3 py-3 first:pt-0 last:pb-0"
              >
                <Icon
                  size={16}
                  strokeWidth={1.75}
                  className={`mt-0.5 shrink-0 ${isCritical ? "text-critical" : "text-muted"}`}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium break-words">
                    <span className="sr-only">{isCritical ? "Critical" : "Check"}: </span>
                    {item.title}
                  </p>
                  <p className="mt-0.5 text-xs text-ink-2">{item.detail}</p>
                </div>
                <button
                  onClick={() => askChat(item.question)}
                  aria-label={`Ask the assistant: ${item.question}`}
                  title={item.question}
                  className="pressable -my-1 min-h-8 shrink-0 text-[13px] text-accent-ink hover:underline"
                >
                  Ask
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
