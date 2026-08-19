"use server";

import { createLead } from "@/lib/api";
import { redirect } from "next/navigation";

export async function submitReservation(formData: FormData) {
  const tourId = String(formData.get("tourId") ?? "").trim();
  const phone = String(formData.get("phone") ?? "").trim();

  if (!tourId) {
    redirect("/reserve?error=tour");
  }

  if (!/^09\d{9}$/.test(phone)) {
    redirect(`/reserve?tourId=${encodeURIComponent(tourId === "consultation" ? "" : tourId)}&error=phone`);
  }

  const lead = await createLead({ tourId, phone });
  redirect(`/reserve/success?ref=${encodeURIComponent(lead.id)}`);
}
