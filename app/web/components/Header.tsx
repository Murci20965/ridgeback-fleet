import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { PipelineStatus } from "@/lib/types";

function DataStatus({ pipeline }: { pipeline: PipelineStatus | null }) {
  if (!pipeline) return null;
  const when = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Johannesburg",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(pipeline.last_run_at));

  if (pipeline.files_failed > 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <CircleAlert size={14} className="text-ink-2" aria-hidden />
        {pipeline.files_failed} {pipeline.files_failed === 1 ? "file" : "files"} failed to load
      </span>
    );
  }
  if (pipeline.files_partial > 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <TriangleAlert size={14} className="text-ink-2" aria-hidden />
        Loaded {when}, with {pipeline.files_partial} incomplete{" "}
        {pipeline.files_partial === 1 ? "file" : "files"}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <CircleCheck size={14} className="text-ink-2" aria-hidden />
      Loaded {when}
    </span>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`pressable rounded-md px-2 py-1 text-[13px] whitespace-nowrap ${
        active ? "font-medium text-ink" : "text-ink-2 hover:text-ink"
      }`}
    >
      {children}
    </Link>
  );
}

export function Header({
  pipeline,
  current,
}: {
  pipeline: PipelineStatus | null;
  current: "dashboard" | "report";
}) {
  return (
    <header className="no-print sticky top-0 z-30 h-12 shrink-0 border-b border-line bg-[color-mix(in_srgb,var(--surface)_72%,transparent)] backdrop-blur-xl">
      <nav
        aria-label="Main"
        className="mx-auto flex h-full w-full max-w-[1480px] items-center justify-between gap-3 px-4 lg:px-6"
      >
        <div className="flex min-w-0 items-baseline gap-2.5">
          {/* The same mark as the tab icon, cropped to the bars so their feet sit on the text's
              baseline. Theme colours make it follow the toggle here. */}
          <svg viewBox="8 7 16 18" className="h-[15px] w-auto shrink-0" fill="var(--ink)" aria-hidden>
            <rect x="8" y="17" width="4" height="8" rx="1" />
            <rect x="14" y="12" width="4" height="13" rx="1" />
            <rect x="20" y="7" width="4" height="18" rx="1" />
          </svg>
          <h1 className="shrink-0 text-[15px] font-semibold tracking-tight">Ridgeback fleet</h1>
          <p className="hidden min-w-0 truncate text-xs text-ink-2 md:block">
            <DataStatus pipeline={pipeline} />
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <NavLink href="/dashboard" active={current === "dashboard"}>
            Dashboard
          </NavLink>
          <NavLink href="/report" active={current === "report"}>
            Report
          </NavLink>
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
