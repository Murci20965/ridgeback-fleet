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
        <CircleAlert size={14} className="text-critical" aria-hidden />
        {pipeline.files_failed} {pipeline.files_failed === 1 ? "file" : "files"} failed to load
      </span>
    );
  }
  if (pipeline.files_partial > 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <TriangleAlert size={14} className="text-warning" aria-hidden />
        Loaded {when}, with {pipeline.files_partial} incomplete{" "}
        {pipeline.files_partial === 1 ? "file" : "files"}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <CircleCheck size={14} className="text-good" aria-hidden />
      Loaded {when}
    </span>
  );
}

export function Header({ pipeline }: { pipeline: PipelineStatus | null }) {
  return (
    <header className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight">Ridgeback fleet</h1>
        <p className="mt-0.5 text-[13px] text-ink-2">
          <DataStatus pipeline={pipeline} />
        </p>
      </div>
      <ThemeToggle />
    </header>
  );
}
