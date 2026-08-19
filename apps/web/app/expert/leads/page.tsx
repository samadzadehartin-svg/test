import { claimLeadAction, updateLeadAction } from "@/app/staff/actions";
import { PanelShell } from "@/components/panel/panel-shell";
import { StatusPill } from "@/components/panel/status-pill";
import { getLeads } from "@/lib/staff-api";
import { getTours } from "@/lib/api";
import { requireStaffRole } from "@/lib/staff-auth";
import type { LeadStatus } from "@/types/staff";

const statusOptions: Array<[LeadStatus, string]> = [["new","جدید"],["contacted","تماس گرفته شد"],["qualified","واجد شرایط"],["reserved","رزرو اولیه"],["won","فروش نهایی"],["lost","از دست رفته"]];
const date = new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

export default async function ExpertLeadsPage() {
  const user = await requireStaffRole("expert");
  const [leads, toursData] = await Promise.all([getLeads(), getTours()]);
  const tourMap = new Map(toursData.items.map((tour) => [tour.id, tour.title]));
  const mine = leads.filter((lead) => lead.assignedExpertId === user.id);
  const queue = leads.filter((lead) => lead.assignedExpertId === null);

  return (
    <PanelShell user={user} current="/expert/leads" title="درخواست‌ها" subtitle="پرونده‌های خودت را به‌روزرسانی کن و فقط در صورت داشتن ظرفیت از صف آزاد درخواست جدید بردار.">
      <section>
        <div className="mb-3 flex items-center justify-between"><h2 className="text-base font-bold">پرونده‌های من</h2><span className="rounded-full bg-white px-3 py-2 text-[8px] text-black/45">{mine.length.toLocaleString("fa-IR")} پرونده</span></div>
        <div className="space-y-3">
          {mine.map((lead) => (
            <details id={`lead-${lead.id}`} key={lead.id} className="rounded-[20px] border border-black/[0.055] bg-white target:ring-2 target:ring-[#b89a64]/30">
              <summary className="grid cursor-pointer list-none gap-3 p-4 sm:grid-cols-[1fr_auto_auto] sm:items-center sm:p-5"><div className="min-w-0"><strong className="block truncate text-[11px]">{tourMap.get(lead.tourId) ?? lead.tourId}</strong><span className="mt-1 block text-[9px] text-black/38" dir="ltr">{lead.phone}</span></div><StatusPill status={lead.status} /><span className="text-[8px] text-black/30">{date.format(new Date(lead.updatedAt))}</span></summary>
              <form action={updateLeadAction} className="grid gap-4 border-t border-black/[0.055] bg-[#faf8f4] p-4 sm:grid-cols-[.8fr_1.5fr_auto] sm:items-end sm:p-5">
                <input type="hidden" name="id" value={lead.id} />
                <label><span className="mb-2 block text-[8px] font-bold text-black/45">وضعیت</span><select name="status" defaultValue={lead.status} className="select select-bordered h-11 w-full rounded-xl bg-white text-[10px]">{statusOptions.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                <label><span className="mb-2 block text-[8px] font-bold text-black/45">یادداشت پیگیری</span><input name="note" defaultValue={lead.note} className="input input-bordered h-11 w-full rounded-xl bg-white text-[10px]" placeholder="بودجه، تاریخ، نتیجه تماس…" /></label>
                <button className="btn h-11 rounded-xl border-0 bg-[#171715] px-5 text-[9px] text-white">ذخیره</button>
              </form>
            </details>
          ))}
          {!mine.length && <div className="rounded-[20px] border border-dashed border-black/10 bg-white py-14 text-center text-[9px] text-black/40">پرونده‌ای به شما تخصیص داده نشده.</div>}
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between"><h2 className="text-base font-bold">صف آزاد</h2><span className="rounded-full bg-[#e9dfcc] px-3 py-2 text-[8px] text-black/50">{queue.length.toLocaleString("fa-IR")} درخواست</span></div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {queue.map((lead) => (
            <form key={lead.id} action={claimLeadAction} className="rounded-[20px] border border-black/[0.055] bg-white p-4"><input type="hidden" name="id" value={lead.id} /><StatusPill status={lead.status} /><strong className="mt-4 block truncate text-[11px]">{tourMap.get(lead.tourId) ?? lead.tourId}</strong><span className="mt-1 block text-[9px] text-black/38" dir="ltr">{lead.phone}</span><button className="mt-4 h-10 w-full rounded-xl bg-[#171715] text-[9px] font-bold text-white">این درخواست را بردار</button></form>
          ))}
        </div>
      </section>
    </PanelShell>
  );
}
