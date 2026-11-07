import { formatCount } from "@/lib/format";
import type { PipelineStatus } from "@/lib/types";

export function PipelineFooter({ pipeline }: { pipeline: PipelineStatus | null }) {
  if (!pipeline) return null;
  return (
    <footer className="mt-4 mb-1 px-1 text-xs text-ink-2">
      {formatCount(pipeline.rows_total)} rows received across {pipeline.files} files:{" "}
      {formatCount(pipeline.rows_loaded)} loaded, {formatCount(pipeline.rows_duplicate)} duplicates
      removed, {formatCount(pipeline.rows_rejected)} rejected with a reason.
    </footer>
  );
}
