import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { INTRO_SCRIPT, LogoIntro } from "@/components/LogoIntro";
import heroPhoto from "@/public/ridgeback-hero.jpg";

type SearchParams = Record<string, string | string[] | undefined>;

/** The way in. It isn't a sign-in: the brief needs a public URL, and the data is fictional. */
export default async function WelcomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  // Filtered links used to live on this address, so they carry on to the dashboard.
  const { day, branch, type } = await searchParams;
  if (day || branch || type) {
    const query = new URLSearchParams();
    for (const [name, value] of Object.entries({ day, branch, type })) {
      if (typeof value === "string") query.set(name, value);
    }
    redirect(`/dashboard?${query}`);
  }

  // The photo sets the mood in both themes, so this page keeps light text over it.
  return (
    <main className="relative grid min-h-dvh place-items-center overflow-hidden bg-black p-4">
      <script dangerouslySetInnerHTML={{ __html: INTRO_SCRIPT }} />
      <LogoIntro />
      {/* The slight blur softens brand names on the machines in the photo. The photo is already
          compressed, and Vercel's image optimiser returns 404 under a Services deployment. */}
      <Image
        src={heroPhoto}
        alt=""
        fill
        priority
        unoptimized
        sizes="100vw"
        className="intro-photo scale-105 object-cover object-[22%_center] blur-[3px] md:object-center"
      />
      <div aria-hidden className="absolute inset-0 bg-linear-to-b from-black/30 via-black/40 to-black/80" />

      <section className="intro-card relative flex w-full max-w-sm flex-col gap-4 rounded-[22px] border border-white/10 bg-black/60 p-8 text-white backdrop-blur-xl">
        <div className="flex items-baseline gap-2.5">
          <svg viewBox="8 7 16 18" className="intro-target h-[19px] w-auto shrink-0" fill="#ffffff" aria-hidden>
            <rect x="8" y="17" width="4" height="8" rx="1" />
            <rect x="14" y="12" width="4" height="13" rx="1" />
            <rect x="20" y="7" width="4" height="18" rx="1" />
          </svg>
          <h1 className="text-2xl leading-tight font-semibold tracking-[-0.02em]">Ridgeback fleet</h1>
        </div>
        <p className="text-sm leading-normal text-white/70">
          How your machines and drivers performed, ready every morning. Ask anything the data can
          answer.
        </p>
        <Link
          href="/dashboard"
          className="pressable block rounded-xl bg-[#17191f] px-4 py-3 text-center text-[15px] font-medium text-[#3b8fd6] hover:bg-[#1f2229]"
        >
          View dashboard
        </Link>
      </section>

      <svg viewBox="8 7 16 18" className="intro-logo" fill="#ffffff" aria-hidden>
        <rect x="8" y="17" width="4" height="8" rx="1" />
        <rect x="14" y="12" width="4" height="13" rx="1" />
        <rect x="20" y="7" width="4" height="18" rx="1" />
      </svg>

      <p className="absolute bottom-4 left-4 text-xs text-white/60">Photo: Duc LE on Unsplash</p>
    </main>
  );
}
