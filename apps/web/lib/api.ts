import type { Tour, TourFilters, TourListResponse } from "@/types/tour";

const API_URL = process.env.API_URL ?? "http://localhost:4000/api";

export async function getTours(filters: TourFilters = {}): Promise<TourListResponse> {
  const url = new URL(`${API_URL}/tours`);

  if (filters.continent) url.searchParams.set("continent", filters.continent);
  if (filters.tripType) url.searchParams.set("tripType", filters.tripType);
  if (filters.budget) url.searchParams.set("budget", filters.budget);

  const response = await fetch(url, {
    next: { revalidate: 120 },
  });

  if (!response.ok) {
    throw new Error("Tour API is unavailable");
  }

  return response.json();
}

export async function getTour(id: string): Promise<Tour | null> {
  const response = await fetch(`${API_URL}/tours/${encodeURIComponent(id)}`, {
    next: { revalidate: 120 },
  });

  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Tour API is unavailable");

  return response.json();
}

export async function createLead(payload: { tourId: string; phone: string }) {
  const response = await fetch(`${API_URL}/leads`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Could not create lead");
  }

  return response.json();
}
