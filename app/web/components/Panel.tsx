export function Panel({
  title,
  subtitle,
  aside,
  className = "",
  children,
}: {
  title: string;
  subtitle?: string;
  aside?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`card min-w-0 p-5 ${className}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-[17px] font-semibold tracking-tight">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-ink-2">{subtitle}</p>}
        </div>
        {aside}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function ShowMore({
  expanded,
  total,
  onClick,
}: {
  expanded: boolean;
  total: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-expanded={expanded}
      className="pressable mt-2 min-h-9 text-[13px] text-accent-ink hover:underline"
    >
      {expanded ? "Show fewer" : `Show all ${total}`}
    </button>
  );
}
