"use client";

export default function ErrorPage({ retry }: { retry: () => void }) {
  return (
    <main className="grid min-h-dvh place-items-center p-6">
      <div className="max-w-sm rounded-xl border border-line bg-surface p-6 text-center">
        <h1 className="font-medium">Couldn&apos;t load the report</h1>
        <p className="mt-1 text-sm text-ink-2">
          The data service didn&apos;t respond. Your data is safe, so try again.
        </p>
        <button
          onClick={() => retry()}
          className="pressable mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
