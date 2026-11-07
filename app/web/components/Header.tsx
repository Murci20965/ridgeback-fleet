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
        <CircleAlert size={14} className="text-[#ff9b9b]" aria-hidden />
        {pipeline.files_failed} {pipeline.files_failed === 1 ? "file" : "files"} failed to load
      </span>
    );
  }
  if (pipeline.files_partial > 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <TriangleAlert size={14} className="text-[#fab219]" aria-hidden />
        Loaded {when}, with {pipeline.files_partial} incomplete{" "}
        {pipeline.files_partial === 1 ? "file" : "files"}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <CircleCheck size={14} className="text-[#5fd38d]" aria-hidden />
      Loaded {when}
    </span>
  );
}

export function Header({ pipeline }: { pipeline: PipelineStatus | null }) {
  return (
    <header className="sticky top-0 z-30 h-14 shrink-0 bg-nav text-white">
      <nav
        aria-label="Main"
        className="mx-auto flex h-full w-full max-w-[1480px] items-center justify-between gap-3 px-4 lg:px-5"
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden>
            <rect width="32" height="32" rx="8" fill="#3987e5" />
            <rect x="8" y="17" width="4" height="8" rx="1" fill="#fff" />
            <rect x="14" y="12" width="4" height="13" rx="1" fill="#fff" />
            <rect x="20" y="7" width="4" height="18" rx="1" fill="#fff" />
          </svg>
          <div className="min-w-0">
            <h1 className="truncate text-base leading-tight font-semibold tracking-tight">
              Ridgeback fleet
            </h1>
            <p className="truncate text-xs text-[#b7c2d0]">
              <DataStatus pipeline={pipeline} />
            </p>
          </div>
        </div>
        <ThemeToggle />
      </nav>
    </header>
  );
}
