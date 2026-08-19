import { claimLeadAction } from "@/app/staff/actions";
import { PanelShell } from "@/components/panel/panel-shell";
import { StatCard } from "@/components/panel/stat-card";
import { StatusPill } from "@/components/panel/status-pill";
import { getExpertDashboard } from "@/lib/staff-api";
import { getTours } from "@/lib/api";
import { requireStaffRole } from "@/lib/staff-auth";

const number = new Intl.NumberFormat("fa-IR");
const time = new Intl.DateTimeFormat("fa-IR", { hour: "2-digit", minute: "2-digit" });

export default async function ExpertDashboardPage() {
  const user = await requireStaffRole("expert");
  const [dashboard, toursData] = await Promise.all([getExpertDashboard(), getTours()]);
  const tourMap = new Map(toursData.items.map((tour) => [tour.id, tour.title]));

  return (
    <PanelShell user={user} current="/expert" title="کارهای امروز" subtitle="اول درخواست‌های جدید و پرونده‌های نزدیک به رزرو را جلو ببر؛ داشبورد فقط چیزهایی را نشان می‌دهد که برای اقدام امروز لازم‌اند.">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="پرونده‌های من" value={number.format(dashboard.stats.total)} hint="کل درخواست‌های تخصیص‌یافته" tone="dark" />
        <StatCard label="امروز" value={number.format(dashboard.stats.today)} hint="درخواست ثبت‌شده امروز" tone="gold" />
        <StatCard label="واجد شرایط" value={number.format(dashboard.stats.qualified)} hint="نیازمند پیگیری فروش" />
        <StatCard label="رزرو اولیه" value={number.format(dashboard.stats.reserved)} hint="نزدیک به نهایی شدن" />
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <div className="rounded-[22px] border border-black/[0.055] bg-white p-4 sm:p-5">
          <div className="flex items-center justify-between"><div><span className="text-[8px] tracking-[0.16em] text-black/35">MY PIPELINE</span><h2 className="mt-1 text-lg font-bold">پیگیری‌های من</h2></div><a href="/expert/leads" className="text-[8px] font-bold text-black/42">مشاهده همه ←</a></div>
          <div className="mt-4 divide-y divide-black/[0.055]">
            {dashboard.mine.length ? dashboard.mine.map((lead) => (
              <a key={lead.id} href={`/expert/leads#lead-${lead.id}`} className="grid gap-3 py-4 sm:grid-cols-[1fr_auto_auto] sm:items-center">
                <div className="min-w-0"><strong className="block truncate text-[11px]">{tourMap.get(lead.tourId) ?? lead.tourId}</strong><span className="mt-1 block text-[9px] text-black/38" dir="ltr">{lead.phone}</span></div>
                <StatusPill status={lead.status} />
                <span className="text-[8px] text-black/30">{time.format(new Date(lead.updatedAt))}</span>
              </a>
            )) : <div className="py-12 text-center text-[9px] text-black/40">هنوز پرونده‌ای به شما تخصیص داده نشده.</div>}
          </div>
        </div>

        <div className="rounded-[22px] border border-black/[0.055] bg-[#e9dfcc] p-5">
          <span className="text-[8px] tracking-[0.16em] text-black/35">NEW QUEUE</span><h2 className="mt-1 text-lg font-bold">صف درخواست‌های آزاد</h2><p className="mt-2 text-[9px] leading-6 text-black/45">فقط وقتی فرصت پیگیری داری یک درخواست را بردار.</p>
          <div className="mt-4 space-y-2">
            {dashboard.queue.length ? dashboard.queue.map((lead) => (
              <form key={lead.id} action={claimLeadAction} className="flex items-center justify-between gap-3 rounded-2xl bg-white/70 p-3">
                <input type="hidden" name="id" value={lead.id} />
                <div className="min-w-0"><strong className="block truncate text-[10px]">{tourMap.get(lead.tourId) ?? lead.tourId}</strong><span className="text-[8px] text-black/35" dir="ltr">{lead.phone}</span></div>
                <button className="shrink-0 rounded-full bg-[#171715] px-3 py-2 text-[8px] font-bold text-white">برداشتن</button>
              </form>
            )) : <div className="rounded-2xl bg-white/60 p-5 text-center text-[9px] text-black/40">صف آزاد خالی است.</div>}
          </div>
        </div>
      </section>

      <section className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-[20px] border border-black/[0.055] bg-white p-4"><span className="text-[8px] text-black/35">اولویت ۱</span><strong className="mt-2 block text-[11px]">Qualified را امروز تماس بگیر</strong><p className="mt-2 text-[9px] leading-6 text-black/40">مشتری که بودجه و مقصدش مشخص شده از درخواست کاملاً جدید ارزش پیگیری بیشتری دارد.</p></div>
        <div className="rounded-[20px] border border-black/[0.055] bg-white p-4"><span className="text-[8px] text-black/35">اولویت ۲</span><strong className="mt-2 block text-[11px]">یادداشت کوتاه ولی دقیق</strong><p className="mt-2 text-[9px] leading-6 text-black/40">بودجه، تعداد نفرات، تاریخ و مانع خرید را ثبت کن تا تماس بعدی از صفر شروع نشود.</p></div>
        <div className="rounded-[20px] border border-black/[0.055] bg-white p-4"><span className="text-[8px] text-black/35">اولویت ۳</span><strong className="mt-2 block text-[11px]">نتیجه را ببند</strong><p className="mt-2 text-[9px] leading-6 text-black/40">پرونده نهایی را Won یا Lost کن تا لیست روزانه تمیز بماند.</p></div>
      </section>
    </PanelShell>
  );
}
