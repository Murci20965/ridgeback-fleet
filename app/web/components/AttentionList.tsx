"use client";

import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import { useChatBridge } from "@/components/ChatBridge";
import { Panel } from "@/components/Panel";
import type { AttentionItem } from "@/lib/types";

const severity = {
  critical: { Icon: CircleAlert, tone: "text-critical", label: "Critical" },
  warning: { Icon: TriangleAlert, tone: "text-warning", label: "Check" },
};

export function AttentionList({ items }: { items: AttentionItem[] }) {
  const { askChat } = useChatBridge();

  return (
    <Panel title="Needs attention" subtitle="What to look at first this morning">
      {items.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-ink-2">
          <CircleCheck size={16} className="text-good" aria-hidden />
          Nothing needs attention for this view.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => {
            const { Icon, tone, label } = severity[item.severity];
            return (
              <li
                key={`${item.kind}-${item.title}`}
                className="flex items-start gap-2.5 py-2 first:pt-0 last:pb-0"
              >
                <Icon size={16} className={`mt-0.5 shrink-0 ${tone}`} aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium break-words">
                    <span className="sr-only">{label}: </span>
                    {item.title}
                  </p>
                  <p className="text-xs text-ink-2">{item.detail}</p>
                </div>
                <button
                  onClick={() => askChat(item.question)}
                  aria-label={`Ask the assistant: ${item.question}`}
                  title={item.question}
                  className="pressable min-h-9 shrink-0 rounded-lg px-2 text-[13px] font-medium text-accent-ink hover:bg-accent-wash"
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
