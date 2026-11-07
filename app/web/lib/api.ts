import type { Dashboard, Filters } from "./types";

// BACKEND_INTERNAL_URL is set by the Vercel Services binding. API_URL is for local development.
const baseUrl = () =>
  process.env.BACKEND_INTERNAL_URL ?? process.env.API_URL ?? "http://localhost:8000";

export class DayOutsideData extends Error {}

export async function fetchDashboard(filters: Filters): Promise<Dashboard> {
  const url = new URL("/api/v1/dashboard", baseUrl());
  if (filters.day) url.searchParams.set("day", filters.day);
  if (filters.branch) url.searchParams.set("branch", filters.branch);
  if (filters.type) url.searchParams.set("machine_type", filters.type);

  // New data only arrives once a day, so a short cache is safe and keeps filters quick.
  const response = await fetch(url, { next: { revalidate: 60 } });
  if (response.status === 422) throw new DayOutsideData();
  if (!response.ok) throw new Error(`Dashboard request failed with ${response.status}`);
  return response.json();
}
