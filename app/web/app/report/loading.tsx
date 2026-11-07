const block = "animate-pulse rounded-[20px] bg-surface-2 motion-reduce:animate-none";

export default function Loading() {
  return (
    <div className="flex min-h-dvh flex-col" role="status" aria-label="Loading the report">
      <div className="h-12 shrink-0 border-b border-line bg-surface" />
      <div className="mx-auto grid w-full max-w-[920px] gap-4 px-4 py-5 lg:py-8">
        <div className={`${block} h-40`} />
        <div className={`${block} h-96`} />
      </div>
    </div>
  );
}
