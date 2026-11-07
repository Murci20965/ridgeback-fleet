const block = "animate-pulse rounded-xl bg-surface-2 motion-reduce:animate-none";

export default function Loading() {
  return (
    <div
      className="mx-auto grid w-full max-w-[1480px] gap-5 p-4 lg:h-dvh lg:grid-cols-[minmax(0,1fr)_380px] lg:p-5"
      role="status"
      aria-label="Loading fleet figures"
    >
      <div className="grid content-start gap-4">
        <div className={`${block} h-12 w-64`} />
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
  );
}
