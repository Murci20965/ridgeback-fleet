"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useTransition } from "react";
import type { Filters } from "@/lib/types";

interface FilterContextValue {
  filters: Filters;
  isPending: boolean;
  setFilter: (key: keyof Filters, value: string | null) => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

export function useFilters() {
  const value = useContext(FilterContext);
  if (!value) throw new Error("useFilters must be used inside FilterProvider");
  return value;
}

/** Filters live in the URL, so a view can be reloaded, shared or reached with the back button. */
export function FilterProvider({
  filters,
  children,
}: {
  filters: Filters;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const setFilter = useCallback(
    (key: keyof Filters, value: string | null) => {
      const next = new URLSearchParams();
      const merged = { ...filters, [key]: value };
      for (const [name, current] of Object.entries(merged)) {
        if (current) next.set(name, current);
      }
      const query = next.toString();
      startTransition(() => {
        router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
      });
    },
    [filters, pathname, router],
  );

  return (
    <FilterContext.Provider value={{ filters, isPending, setFilter }}>
      {children}
    </FilterContext.Provider>
  );
}

/** Dims the current figures while new ones load, instead of blanking the page. */
export function PendingFrame({ children }: { children: React.ReactNode }) {
  const { isPending } = useFilters();
  return (
    <div
      aria-busy={isPending}
      className={`transition-opacity duration-150 ${isPending ? "opacity-60" : ""}`}
    >
      {children}
    </div>
  );
}
