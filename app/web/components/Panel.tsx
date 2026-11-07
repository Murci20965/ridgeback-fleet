export function Panel({
  title,
  subtitle,
  className = "",
  children,
}: {
  title: string;
  subtitle?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`min-w-0 rounded-xl border border-line bg-surface p-4 ${className}`}>
      <h3 className="text-sm font-semibold">{title}</h3>
      {subtitle && <p className="mt-0.5 text-xs text-ink-2">{subtitle}</p>}
      <div className="mt-3">{children}</div>
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
      className="pressable mt-2 min-h-9 rounded-lg px-2 text-[13px] font-medium text-accent-ink hover:bg-accent-wash"
    >
      {expanded ? "Show fewer" : `Show all ${total}`}
    </button>
  );
}
