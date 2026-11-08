import type { Metadata } from "next";
import { CircleCheck, Info } from "lucide-react";
import { Header } from "@/components/Header";
import { PrintButton } from "@/components/PrintButton";
import { BarChart, ColumnChart } from "@/components/ReportCharts";
import { fetchLatestReport } from "@/lib/api";
import { formatCount, formatHours, fullDay, shortDate, shortWeekday } from "@/lib/format";
import type { ReportFacts, WeeklyReport } from "@/lib/types";

// The report changes when the pipeline publishes one, and the API isn't reachable during a build.
export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const report = await fetchLatestReport();
  // The browser offers this title as the file name when saving a PDF.
  return {
    title: report
      ? `Ridgeback fleet report, ${shortDate(report.week_start)} to ${shortDate(report.week_end)} ${report.week_end.slice(0, 4)}`
      : "Ridgeback fleet report",
  };
}

const generatedFormat = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Africa/Johannesburg",
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="kpi-tile rounded-2xl bg-page p-4">
      <p className="text-xs text-ink-2">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{value}</p>
      {note && <p className="mt-0.5 text-xs text-ink-2">{note}</p>}
    </div>
  );
}

function Points({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="report-section">
      <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>
      <ul className="mt-2 grid gap-2 text-sm leading-relaxed">
        {items.map((item) => (
          <li key={item} className="flex gap-2.5">
            <span aria-hidden className="mt-[9px] size-1 shrink-0 rounded-full bg-ink-2" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Table({
  title,
  headings,
  rows,
}: {
  title: string;
  headings: string[];
  rows: (string | number)[][];
}) {
  return (
    <section className="report-section min-w-0">
      <h3 className="text-[15px] font-semibold tracking-tight">{title}</h3>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line-strong text-left text-xs text-ink-2">
              {headings.map((heading, index) => (
                <th
                  key={heading}
                  scope="col"
                  className={`py-1.5 font-medium ${index === 0 ? "" : "pl-3 text-right"}`}
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row[0])} className="border-b border-line last:border-0">
                {row.map((cell, index) => (
                  <td
                    key={headings[index]}
                    className={`py-1.5 whitespace-nowrap ${index === 0 ? "" : "pl-3 text-right tabular-nums"}`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DataNotes({ facts }: { facts: ReportFacts }) {
  const { pipeline } = facts;
  return (
    <section className="report-section mt-8 border-t border-line pt-5">
      <h3 className="text-[15px] font-semibold tracking-tight">Data notes</h3>
      {facts.days_with_data < 7 && (
        <p className="mt-2 text-[13px] text-ink-2">
          This week has data for {facts.days_with_data} of 7 days, so its figures are incomplete.
        </p>
      )}
      <ul className="mt-2 grid gap-2 text-[13px] leading-snug">
        {facts.attention.map((item) => (
          <li key={item.title}>
            <span className={item.severity === "critical" ? "font-medium text-critical" : "font-medium"}>
              {item.title}.
            </span>{" "}
            <span className="text-ink-2">{item.detail}</span>
          </li>
        ))}
      </ul>
      {pipeline && (
        <p className="mt-3 text-[13px] text-ink-2">
          Across {pipeline.files} files, {formatCount(pipeline.rows_total)} rows arrived:{" "}
          {formatCount(pipeline.rows_loaded)} loaded, {formatCount(pipeline.rows_duplicate)}{" "}
          duplicates and {formatCount(pipeline.rows_rejected)} rejected with a reason.
        </p>
      )}
    </section>
  );
}

function Report({ report }: { report: WeeklyReport }) {
  const { facts, commentary } = report;
  const { kpis } = facts;
  const modelName = report.model?.split("/").pop();
  const unattributed =
    kpis.unattributed_impacts > 0 ? `${kpis.unattributed_impacts} with no driver` : undefined;

  return (
    <article className="report card p-5 sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[13px] text-ink-2">
            {fullDay(report.week_start)} to {fullDay(report.week_end)}{" "}
            {report.week_end.slice(0, 4)}
          </p>
          <h2 className="mt-0.5 text-2xl font-semibold tracking-tight">Weekly fleet report</h2>
        </div>
        <PrintButton />
      </div>

      <p className="mt-5 text-[15px] leading-relaxed">{commentary?.summary ?? facts.headline}</p>
      <p className="mt-2 flex items-start gap-1.5 text-xs text-ink-2">
        {commentary ? (
          <CircleCheck size={13} className="mt-px shrink-0" aria-hidden />
        ) : (
          <Info size={13} className="mt-px shrink-0" aria-hidden />
        )}
        {commentary
          ? `Written by ${modelName ?? "an AI model"} from the figures below. Its figures were checked against the data before publishing.`
          : "The written commentary isn't available this week. The figures below come straight from the data."}
      </p>

      <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Run hours" value={formatHours(kpis.run_hours)} />
        <Kpi label="Active machines" value={`${kpis.active_machines} of ${kpis.fleet_size}`} />
        <Kpi label="Impacts" value={formatCount(kpis.impacts)} note={unattributed} />
        <Kpi label="Harsh events" value={formatCount(kpis.harsh_events)} />
      </div>

      {commentary && (
        <div className="report-columns mt-7 grid gap-6 md:grid-cols-2">
          <Points title="Highlights" items={commentary.highlights} />
          {commentary.checks.length > 0 && (
            <Points title="Worth checking this week" items={commentary.checks} />
          )}
        </div>
      )}

      <div className="report-columns mt-8 grid gap-x-8 gap-y-8 md:grid-cols-2">
        <ColumnChart
          title="Run hours by day"
          points={facts.daily.map((row) => ({
            label: shortWeekday(row.event_date),
            value: row.run_hours,
            display: formatHours(row.run_hours),
            detail: `${fullDay(row.event_date)}: ${formatHours(row.run_hours)} hours`,
          }))}
        />
        <ColumnChart
          title="Impacts by day"
          points={facts.daily.map((row) => ({
            label: shortWeekday(row.event_date),
            value: row.impacts,
            display: formatCount(row.impacts),
            detail: `${fullDay(row.event_date)}: ${formatCount(row.impacts)} impacts`,
          }))}
        />
        <BarChart
          title="Run hours by branch"
          points={facts.branches.map((row) => ({
            label: row.branch,
            value: row.run_hours,
            display: formatHours(row.run_hours),
            detail: `${row.branch}: ${formatHours(row.run_hours)} hours`,
          }))}
        />
        <BarChart
          title="Impacts by branch"
          points={[...facts.branches]
            .sort((a, b) => b.impacts - a.impacts)
            .map((row) => ({
              label: row.branch,
              value: row.impacts,
              display: formatCount(row.impacts),
              detail: `${row.branch}: ${formatCount(row.impacts)} impacts`,
            }))}
        />
        <BarChart
          title="Most used machines"
          points={facts.top_machines.map((row) => ({
            label: `${row.ref_no}, ${row.machine_type}`,
            value: row.run_hours,
            display: formatHours(row.run_hours),
            detail: `${row.ref_no}: ${formatHours(row.run_hours)} hours`,
          }))}
        />
        <BarChart
          title="Most impacts by driver"
          points={facts.top_drivers.map((row) => ({
            label: row.driver_name ?? "No driver logged on",
            value: row.impacts,
            display: formatCount(row.impacts),
            detail: `${row.driver_name}: ${formatCount(row.impacts)} impacts, ${formatCount(row.harsh)} harsh events`,
          }))}
        />
      </div>

      <div className="report-columns mt-8 grid gap-x-8 gap-y-7 border-t border-line pt-6 md:grid-cols-2">
        <Table
          title="By branch"
          headings={["Branch", "Hours", "Machines", "Impacts", "Harsh"]}
          rows={facts.branches.map((row) => [
            row.branch,
            formatHours(row.run_hours),
            row.active_machines,
            row.impacts,
            row.harsh,
          ])}
        />
        <Table
          title="By day"
          headings={["Day", "Hours", "Machines", "Impacts", "Harsh"]}
          rows={facts.daily.map((row) => [
            fullDay(row.event_date),
            formatHours(row.run_hours),
            row.active_machines,
            row.impacts,
            row.harsh_events,
          ])}
        />
      </div>

      <DataNotes facts={facts} />

      <p className="mt-5 text-xs text-ink-2">
        Generated {generatedFormat.format(new Date(report.generated_at))} by the pipeline. It runs
        every Monday at 07:07 SAST and covers the latest full week of data.
      </p>
    </article>
  );
}

export default async function ReportPage() {
  const report = await fetchLatestReport();

  return (
    <div className="flex min-h-dvh flex-col">
      <Header pipeline={null} current="report" />
      <main className="report-main mx-auto w-full max-w-[920px] flex-1 px-4 py-5 lg:py-8">
        {report ? (
          <Report report={report} />
        ) : (
          <div className="card p-8 text-center">
            <h2 className="font-medium">No report yet</h2>
            <p className="mt-1 text-sm text-ink-2">
              The first report appears after the pipeline&apos;s Monday 07:07 SAST run.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
