/** The view's summary, with the first sentence leading and the rest quieter. */
export function Headline({ dates, text }: { dates: string; text: string }) {
  // A figure like 1,052.7 has no space after its point, so this only splits between sentences.
  const [lead, ...rest] = text.split(/(?<=\.)\s/);

  return (
    <div className="mt-5 mb-3 lg:mt-3">
      <p className="text-[13px] font-medium text-ink-2">{dates}</p>
      <h2 className="mt-1.5 max-w-4xl text-[26px] leading-[1.15] font-semibold tracking-[-0.022em] text-balance md:text-[34px]">
        {lead} <span className="text-ink-2">{rest.join(" ")}</span>
      </h2>
    </div>
  );
}
