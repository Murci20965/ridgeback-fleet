"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useOptimistic, useTransition } from "react";
import type { Filters } from "@/lib/types";

interface FilterContextValue {
  filters: Filters;
  isPending: boolean;
  setFilter: (key: keyof Filters, value: string | null) => void;
  setFilters: (next: Filters) => void;
  clearFilters: () => void;
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
  // Controls show the new choice at once, while the figures for it load.
  const [optimistic, setOptimistic] = useOptimistic(filters);

  const navigate = useCallback(
    (next: Filters) => {
      const params = new URLSearchParams();
      for (const [name, current] of Object.entries(next)) {
        if (current) params.set(name, current);
      }
      const query = params.toString();
      startTransition(() => {
        setOptimistic(next);
        router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
      });
    },
    [pathname, router, setOptimistic],
  );

  const setFilter = useCallback(
    (key: keyof Filters, value: string | null) => navigate({ ...optimistic, [key]: value }),
    [navigate, optimistic],
  );
  const clearFilters = useCallback(
    () => navigate({ day: null, branch: null, type: null }),
    [navigate],
  );

  return (
    <FilterContext.Provider value={{ filters: optimistic, isPending, setFilter, setFilters: navigate, clearFilters }}>
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
