"use server";

import { clearStaffSession, loginStaff, setStaffSession, updateLead, claimLead, updateManagedTour } from "@/lib/staff-api";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

export async function loginAction(formData: FormData) {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const result = await loginStaff(username, password);

  if (!result) redirect("/staff/login?error=1");

  await setStaffSession(result.token, result.expiresAt);
  redirect(result.user.role === "admin" ? "/admin" : "/expert");
}

export async function logoutAction() {
  await clearStaffSession();
  redirect("/staff/login");
}

export async function updateLeadAction(formData: FormData) {
  const id = String(formData.get("id") ?? "");
  const status = String(formData.get("status") ?? "");
  const note = String(formData.get("note") ?? "");
  const assigned = formData.get("assignedExpertId");

  await updateLead(id, {
    status: status || undefined,
    note,
    assignedExpertId: assigned === null ? undefined : String(assigned) || null,
  });

  revalidatePath("/admin");
  revalidatePath("/admin/leads");
  revalidatePath("/admin/team");
  revalidatePath("/expert");
  revalidatePath("/expert/leads");
}

export async function claimLeadAction(formData: FormData) {
  const id = String(formData.get("id") ?? "");
  await claimLead(id);
  revalidatePath("/expert");
  revalidatePath("/expert/leads");
}

export async function updateTourAction(formData: FormData) {
  const id = String(formData.get("id") ?? "");
  const priceRaw = String(formData.get("price") ?? "").replaceAll(",", "").trim();
  const active = formData.get("active") === "on";
  const tag = String(formData.get("tag") ?? "").trim();

  await updateManagedTour(id, {
    price: priceRaw ? Number(priceRaw) : null,
    active,
    tag: tag || undefined,
  });

  revalidatePath("/admin");
  revalidatePath("/admin/tours");
  revalidatePath("/");
}
