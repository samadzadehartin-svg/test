import { updateLeadAction } from "@/app/staff/actions";
import { PanelShell } from "@/components/panel/panel-shell";
import { StatusPill } from "@/components/panel/status-pill";
import { getExperts, getLeads, getManagedTours } from "@/lib/staff-api";
import { requireStaffRole } from "@/lib/staff-auth";
import type { LeadStatus } from "@/types/staff";

const statusOptions: Array<[LeadStatus, string]> = [["new","جدید"],["contacted","تماس گرفته شد"],["qualified","واجد شرایط"],["reserved","رزرو اولیه"],["won","فروش نهایی"],["lost","از دست رفته"]];
const date = new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

type Params = Promise<{ status?: string }>;

export default async function AdminLeadsPage({ searchParams }: { searchParams: Params }) {
  const user = await requireStaffRole("admin");
  const query = await searchParams;
  const [leads, experts, tours] = await Promise.all([getLeads(), getExperts(), getManagedTours()]);
  const tourMap = new Map(tours.map((tour) => [tour.id, tour.title]));
  const expertMap = new Map(experts.map((expert) => [expert.id, expert.name]));
  const filtered = query.status ? leads.filter((lead) => lead.status === query.status) : leads;

  return (
    <PanelShell user={user} current="/admin/leads" title="مدیریت درخواست‌ها" subtitle="هر درخواست یک مالک و وضعیت مشخص دارد؛ یادداشت پیگیری را همین‌جا نگه دار تا اطلاعات بین کارشناسان گم نشود.">
      <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
        <a href="/admin/leads" className={`shrink-0 rounded-full px-4 py-2 text-[8px] font-bold ${!query.status ? "bg-[#171715] text-white" : "bg-white text-black/45"}`}>همه</a>
        {statusOptions.map(([value,label]) => <a key={value} href={`/admin/leads?status=${value}`} className={`shrink-0 rounded-full px-4 py-2 text-[8px] font-bold ${query.status === value ? "bg-[#171715] text-white" : "bg-white text-black/45"}`}>{label}</a>)}
      </div>

      <div className="space-y-3">
        {filtered.map((lead) => (
          <details key={lead.id} className="group rounded-[20px] border border-black/[0.055] bg-white open:shadow-sm">
            <summary className="grid cursor-pointer list-none gap-3 p-4 sm:grid-cols-[1.2fr_.7fr_auto_auto] sm:items-center sm:p-5">
              <div className="min-w-0"><strong className="block truncate text-[11px]">{tourMap.get(lead.tourId) ?? lead.tourId}</strong><span className="mt-1 block text-[9px] text-black/38" dir="ltr">{lead.phone}</span></div>
              <div><span className="block text-[8px] text-black/35">کارشناس</span><strong className="mt-1 block text-[9px]">{lead.assignedExpertId ? expertMap.get(lead.assignedExpertId) ?? "نامشخص" : "بدون تخصیص"}</strong></div>
              <StatusPill status={lead.status} />
              <span className="text-[8px] text-black/32">{date.format(new Date(lead.createdAt))}</span>
            </summary>
            <form action={updateLeadAction} className="grid gap-4 border-t border-black/[0.055] bg-[#faf8f4] p-4 sm:grid-cols-2 sm:p-5 lg:grid-cols-[.7fr_.8fr_1.5fr_auto] lg:items-end">
              <input type="hidden" name="id" value={lead.id} />
              <label><span className="mb-2 block text-[8px] font-bold text-black/45">وضعیت</span><select name="status" defaultValue={lead.status} className="select select-bordered h-11 w-full rounded-xl bg-white text-[10px]">{statusOptions.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label><span className="mb-2 block text-[8px] font-bold text-black/45">کارشناس</span><select name="assignedExpertId" defaultValue={lead.assignedExpertId ?? ""} className="select select-bordered h-11 w-full rounded-xl bg-white text-[10px]"><option value="">بدون تخصیص</option>{experts.map((expert) => <option key={expert.id} value={expert.id}>{expert.name}</option>)}</select></label>
              <label><span className="mb-2 block text-[8px] font-bold text-black/45">یادداشت پیگیری</span><input name="note" defaultValue={lead.note} className="input input-bordered h-11 w-full rounded-xl bg-white text-[10px]" placeholder="نتیجه تماس، بودجه، تاریخ موردنظر…" /></label>
              <button className="btn h-11 rounded-xl border-0 bg-[#171715] px-5 text-[9px] text-white hover:bg-black">ذخیره</button>
            </form>
          </details>
        ))}
      </div>
    </PanelShell>
  );
}
