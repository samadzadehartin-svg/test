import { cookies } from "next/headers";
import type { Tour } from "@/types/tour";
import type { AdminDashboard, ExpertDashboard, ExpertSummary, Lead, StaffUser } from "@/types/staff";

const API_URL = process.env.API_URL ?? "http://localhost:4000/api";
const SESSION_COOKIE = "safaro_staff_session";

async function token() {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value;
}

async function staffFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const sessionToken = await token();
  if (!sessionToken) throw new Error("UNAUTHENTICATED");

  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${sessionToken}`);
  if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (response.status === 401 || response.status === 403) throw new Error("UNAUTHENTICATED");
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function loginStaff(username: string, password: string) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
    cache: "no-store",
  });
  if (!response.ok) return null;
  return response.json() as Promise<{ token: string; expiresAt: number; user: StaffUser }>;
}

export async function setStaffSession(value: string, expiresAt: number) {
  const store = await cookies();
  store.set(SESSION_COOKIE, value, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(expiresAt),
  });
}

export async function clearStaffSession() {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
}

export async function getStaffUser(): Promise<StaffUser | null> {
  try {
    return await staffFetch<StaffUser>("/auth/me");
  } catch {
    return null;
  }
}

export function getAdminDashboard() {
  return staffFetch<AdminDashboard>("/staff/admin/dashboard");
}

export function getExpertDashboard() {
  return staffFetch<ExpertDashboard>("/staff/expert/dashboard");
}

export function getLeads() {
  return staffFetch<Lead[]>("/leads");
}

export function getExperts() {
  return staffFetch<ExpertSummary[]>("/staff/experts");
}

export function getManagedTours() {
  return staffFetch<Array<Tour & { active: boolean }>>("/staff/tours");
}

export function updateLead(id: string, payload: { status?: string; note?: string; assignedExpertId?: string | null }) {
  return staffFetch<Lead>(`/leads/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function claimLead(id: string) {
  return staffFetch<Lead>(`/leads/${encodeURIComponent(id)}/claim`, { method: "POST" });
}

export function updateManagedTour(id: string, payload: { price?: number | null; active?: boolean; tag?: string }) {
  return staffFetch<Tour & { active: boolean }>(`/staff/tours/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
