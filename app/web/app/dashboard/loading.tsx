const block = "animate-pulse rounded-[20px] bg-surface-2 motion-reduce:animate-none";

export default function Loading() {
  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh" role="status" aria-label="Loading fleet figures">
      <div className="h-12 shrink-0 border-b border-line bg-surface" />
      <div className="mx-auto grid min-h-0 w-full max-w-[1480px] flex-1 gap-5 p-4 lg:grid-cols-[minmax(0,1fr)_380px] lg:p-5 lg:pt-3">
        <div className="grid content-start gap-4">
          <div className={`${block} h-10 w-full`} />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[0, 1, 2, 3].map((tile) => (
              <div key={tile} className={`${block} h-24`} />
            ))}
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            {[0, 1, 2, 3].map((panel) => (
              <div key={panel} className={`${block} h-72`} />
            ))}
          </div>
        </div>
        <div className={`${block} hidden lg:block`} />
      </div>
    </div>
  );
}
