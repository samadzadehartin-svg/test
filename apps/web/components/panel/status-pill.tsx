import type { LeadStatus } from "@/types/staff";

const meta: Record<LeadStatus, { label: string; className: string }> = {
  new: { label: "جدید", className: "bg-blue-50 text-blue-700" },
  contacted: { label: "تماس گرفته شد", className: "bg-amber-50 text-amber-700" },
  qualified: { label: "واجد شرایط", className: "bg-violet-50 text-violet-700" },
  reserved: { label: "رزرو اولیه", className: "bg-cyan-50 text-cyan-700" },
  won: { label: "فروش نهایی", className: "bg-emerald-50 text-emerald-700" },
  lost: { label: "از دست رفته", className: "bg-rose-50 text-rose-700" },
};

export function StatusPill({ status }: { status: LeadStatus }) {
  const item = meta[status];
  return <span className={`inline-flex min-h-7 items-center rounded-full px-2.5 text-[8px] font-bold ${item.className}`}>{item.label}</span>;
}
