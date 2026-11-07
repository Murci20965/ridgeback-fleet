import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
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

export function Header({ pipeline }: { pipeline: PipelineStatus | null }) {
  return (
    <header className="sticky top-0 z-30 h-12 shrink-0 border-b border-line bg-[color-mix(in_srgb,var(--surface)_72%,transparent)] backdrop-blur-xl">
      <nav
        aria-label="Main"
        className="mx-auto flex h-full w-full max-w-[1480px] items-center justify-between gap-3 px-4 lg:px-6"
      >
        <div className="flex min-w-0 items-center gap-2.5">
          {/* The same mark as the tab icon. Theme colours make it follow the toggle here. */}
          <svg viewBox="6 5 20 22" className="size-5 shrink-0" fill="var(--ink)" aria-hidden>
            <rect x="8" y="17" width="4" height="8" rx="1" />
            <rect x="14" y="12" width="4" height="13" rx="1" />
            <rect x="20" y="7" width="4" height="18" rx="1" />
          </svg>
          <h1 className="shrink-0 text-[15px] font-semibold tracking-tight">Ridgeback fleet</h1>
          <p className="min-w-0 truncate text-xs text-ink-2">
            <DataStatus pipeline={pipeline} />
          </p>
        </div>
        <ThemeToggle />
      </nav>
    </header>
  );
}
