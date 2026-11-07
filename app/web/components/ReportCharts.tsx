// The report's charts are plain HTML, drawn on the server. Unlike a chart library that measures
// the window, they need no JavaScript and scale cleanly onto an A4 page when saved as a PDF.

export interface ChartPoint {
  label: string;
  value: number;
  display: string;
  /** The full wording shown when hovering, such as "Tue 8 Sep: 33 impacts". */
  detail: string;
}

/** Two gridline steps with round values, such as 0, 20 and 40 for a highest value of 33. */
function axisFor(highest: number): { step: number; top: number } {
  const rough = Math.max(highest, 1) / 2;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const nice = [1, 2, 2.5, 5, 10].find((option) => option * magnitude >= rough) ?? 10;
  const step = nice * magnitude;
  return { step, top: step * Math.ceil(Math.max(highest, 1) / step) };
}

/** Columns over time, with the highest value darkened and labelled so it reads at a glance. */
export function ColumnChart({ title, points }: { title: string; points: ChartPoint[] }) {
  const highest = Math.max(...points.map((point) => point.value));
  const { step, top } = axisFor(highest);
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, index) => index * step);
  const peak = points.find((point) => point.value === highest);

  return (
    <section className="report-section min-w-0">
      <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>
      <div
        role="img"
        aria-label={`${title}. Highest: ${peak?.detail ?? "none"}. The table below has every figure.`}
        className="relative mt-7 ml-7 h-32"
      >
        {ticks.map((tick) => (
          <div
            key={tick}
            aria-hidden
            className={`absolute inset-x-0 border-t ${tick === 0 ? "border-line-strong" : "border-line"}`}
            style={{ bottom: `${(tick / top) * 100}%` }}
          >
            <span className="absolute right-full mr-1.5 -translate-y-1/2 text-[11px] text-muted tabular-nums">
              {tick}
            </span>
          </div>
        ))}
        <div className="absolute inset-0 flex gap-[2px]">
          {points.map((point) => {
            const height = (point.value / top) * 100;
            const isPeak = point.value === highest && highest > 0;
            return (
              <div key={point.label} title={point.detail} className="relative h-full flex-1">
                <div
                  className={`chart-mark absolute inset-x-[14%] bottom-0 rounded-t ${isPeak ? "bg-chart-peak" : "bg-chart"}`}
                  style={{ height: `${height}%` }}
                />
                {isPeak && (
                  <span
                    className="absolute inset-x-0 text-center text-xs font-medium whitespace-nowrap tabular-nums"
                    style={{ bottom: `calc(${height}% + 2px)` }}
                  >
                    {point.display}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <div aria-hidden className="mt-1.5 ml-7 flex gap-[2px] text-[11px] text-ink-2">
        {points.map((point) => (
          <span key={point.label} className="flex-1 text-center">
            {point.label}
          </span>
        ))}
      </div>
    </section>
  );
}

/** Ranked horizontal bars. A name and value sit above each bar, so long references still fit. */
export function BarChart({ title, points }: { title: string; points: ChartPoint[] }) {
  const highest = Math.max(...points.map((point) => point.value), 1);

  return (
    <section className="report-section min-w-0">
      <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>
      <ul className="mt-3 grid gap-2.5">
        {points.map((point) => (
          <li key={point.label} title={point.detail}>
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="min-w-0 truncate">{point.label}</span>
              <span className="font-medium tabular-nums">{point.display}</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-page">
              <div
                className={`chart-mark h-full rounded-full ${point.value === highest ? "bg-chart-peak" : "bg-chart"}`}
                style={{ width: `${(point.value / highest) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
