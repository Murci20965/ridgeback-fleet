"use client";

import { Download } from "lucide-react";

/** Opens the browser's print dialog, which offers Save as PDF. The print styles do the layout. */
export function PrintButton() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="pressable no-print inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-filter px-3 text-[13px] font-medium"
    >
      <Download size={14} aria-hidden />
      Save as PDF
    </button>
  );
}
