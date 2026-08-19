import { PanelShell } from "@/components/panel/panel-shell";
import { StatCard } from "@/components/panel/stat-card";
import { StatusPill } from "@/components/panel/status-pill";
import { getAdminDashboard, getLeads, getManagedTours } from "@/lib/staff-api";
import { requireStaffRole } from "@/lib/staff-auth";

const money = new Intl.NumberFormat("fa-IR");
const number = new Intl.NumberFormat("fa-IR");
const date = new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

export default async function AdminDashboardPage() {
  const user = await requireStaffRole("admin");
  const [dashboard, leads, tours] = await Promise.all([getAdminDashboard(), getLeads(), getManagedTours()]);
  const tourMap = new Map(tours.map((tour) => [tour.id, tour.title]));
  const recent = leads.slice(0, 6);

  return (
    <PanelShell user={user} current="/admin" title="داشبورد مدیریت" subtitle="تصویر کوتاه از فروش، درخواست‌های جدید و وضعیت تیم؛ جزئیات در صفحات تخصصی قرار دارد.">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="کل درخواست‌ها" value={number.format(dashboard.leads.total)} hint={`${number.format(dashboard.leads.unassigned)} درخواست بدون کارشناس`} tone="dark" />
        <StatCard label="فروش نهایی" value={number.format(dashboard.leads.won)} hint={`نرخ تبدیل ${number.format(dashboard.conversion)}٪`} tone="gold" />
        <StatCard label="تورهای فعال" value={number.format(dashboard.tours.active)} hint={`از ${number.format(dashboard.tours.total)} تور`} />
        <StatCard label="ارزش فروش ثبت‌شده" value={`${money.format(dashboard.estimatedRevenue)} ت.`} hint="بر اساس قیمت تورهای won" />
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
        <div className="rounded-[22px] border border-black/[0.055] bg-white p-4 sm:p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <span className="text-[8px] tracking-[0.16em] text-black/35">LATEST LEADS</span>
              <h2 className="mt-1 text-lg font-bold">درخواست‌های اخیر</h2>
            </div>
            <a href="/admin/leads" className="rounded-full bg-[#f1ede6] px-3 py-2 text-[8px] font-bold text-black/55">همه درخواست‌ها ←</a>
          </div>

          <div className="mt-4 divide-y divide-black/[0.055]">
            {recent.map((lead) => (
              <div key={lead.id} className="grid gap-3 py-4 sm:grid-cols-[1fr_auto_auto] sm:items-center">
                <div className="min-w-0">
                  <strong className="block truncate text-[11px]">{tourMap.get(lead.tourId) ?? lead.tourId}</strong>
                  <span className="mt-1 block text-[9px] text-black/38" dir="ltr">{lead.phone}</span>
                </div>
                <StatusPill status={lead.status} />
                <span className="text-[8px] text-black/35">{date.format(new Date(lead.createdAt))}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[22px] border border-black/[0.055] bg-[#171715] p-5 text-white">
          <span className="text-[8px] tracking-[0.16em] text-white/35">PIPELINE</span>
          <h2 className="mt-1 text-lg font-bold">قیف فروش</h2>
          <div className="mt-5 space-y-4">
            {[
              ["جدید", dashboard.leads.new],
              ["واجد شرایط", dashboard.leads.qualified],
              ["رزرو اولیه", dashboard.leads.reserved],
              ["فروش نهایی", dashboard.leads.won],
            ].map(([label, value]) => {
              const count = Number(value);
              const width = dashboard.leads.total ? Math.max(6, Math.round((count / dashboard.leads.total) * 100)) : 0;
              return (
                <div key={String(label)}>
                  <div className="flex justify-between text-[9px]"><span className="text-white/48">{label}</span><strong>{number.format(count)}</strong></div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/8"><div className="h-full rounded-full bg-[#ded2bb]" style={{ width: `${width}%` }} /></div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mt-5 rounded-[22px] border border-black/[0.055] bg-white p-4 sm:p-5">
        <div className="flex items-center justify-between">
          <div><span className="text-[8px] tracking-[0.16em] text-black/35">TEAM</span><h2 className="mt-1 text-lg font-bold">بار کاری کارشناسان</h2></div>
          <a href="/admin/team" className="text-[8px] font-bold text-black/42">مشاهده تیم ←</a>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {dashboard.experts.map((expert) => (
            <article key={expert.id} className="rounded-2xl bg-[#f4f1eb] p-4">
              <div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-full bg-white text-[9px] font-bold">{expert.initials}</span><div><strong className="block text-[10px]">{expert.name}</strong><small className="text-[8px] text-black/38">داخلی {expert.extension}</small></div></div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center"><div><strong className="block text-sm">{number.format(expert.assigned)}</strong><span className="text-[7px] text-black/35">کل</span></div><div><strong className="block text-sm">{number.format(expert.open)}</strong><span className="text-[7px] text-black/35">باز</span></div><div><strong className="block text-sm">{number.format(expert.won)}</strong><span className="text-[7px] text-black/35">فروش</span></div></div>
            </article>
          ))}
        </div>
      </section>
    </PanelShell>
  );
}
