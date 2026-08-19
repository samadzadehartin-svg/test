import { getStaffUser } from "@/lib/staff-api";
import type { StaffRole } from "@/types/staff";
import { redirect } from "next/navigation";

export async function requireStaffRole(role: StaffRole) {
  const user = await getStaffUser();
  if (!user) redirect("/staff/login");
  if (user.role !== role) redirect(user.role === "admin" ? "/admin" : "/expert");
  return user;
}
