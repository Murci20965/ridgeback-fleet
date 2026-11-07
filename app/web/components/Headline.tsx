import { rangeLabel } from "@/lib/format";
import type { Filters } from "@/lib/types";

/** What's in view as a quiet label, then the one thing that stands out. */
export function Headline({
  filters,
  from,
  to,
  text,
}: {
  filters: Filters;
  from: string;
  to: string;
  text: string;
}) {
  const scope = [filters.branch, filters.type, rangeLabel(from, to)].filter(Boolean).join(" · ");

  return (
    <div className="mt-5 mb-3 lg:mt-3">
      <p className="text-[13px] text-ink-2">{scope}</p>
      <h2
        key={text}
        className="soft-in mt-1 text-[24px] leading-tight font-semibold tracking-[-0.02em] md:text-[28px]"
      >
        {text}
      </h2>
    </div>
  );
}
