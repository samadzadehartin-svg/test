import { PanelShell } from "@/components/panel/panel-shell";
import { getExperts } from "@/lib/staff-api";
import { requireStaffRole } from "@/lib/staff-auth";

const number = new Intl.NumberFormat("fa-IR");

export default async function AdminTeamPage() {
  const user = await requireStaffRole("admin");
  const experts = await getExperts();

  return (
    <PanelShell user={user} current="/admin/team" title="کارشناسان فروش" subtitle="در این نسخه سبک، تمرکز روی بار کاری و خروجی تیم است؛ اتصال شیفت، سطح دسترسی و منابع انسانی می‌تواند در مرحله دیتابیس اضافه شود.">
      <div className="grid gap-4 lg:grid-cols-3">
        {experts.map((expert, index) => {
          const closeRate = expert.assigned ? Math.round((expert.won / expert.assigned) * 100) : 0;
          return (
            <article key={expert.id} className={`rounded-[22px] border border-black/[0.055] p-5 ${index === 0 ? "bg-[#171715] text-white" : "bg-white"}`}>
              <div className="flex items-center justify-between"><span className={`grid h-11 w-11 place-items-center rounded-full text-[10px] font-bold ${index === 0 ? "bg-white text-black" : "bg-[#eee8dc]"}`}>{expert.initials}</span><span className={`rounded-full px-2 py-1 text-[7px] font-bold ${expert.active ? "bg-emerald-50 text-emerald-700" : "bg-black/5 text-black/40"}`}>{expert.active ? "فعال" : "غیرفعال"}</span></div>
              <h2 className="mt-5 text-base font-bold">{expert.name}</h2><span className={`mt-1 block text-[8px] ${index === 0 ? "text-white/35" : "text-black/35"}`}>داخلی {expert.extension}</span>
              <div className={`mt-5 grid grid-cols-3 gap-2 border-t pt-4 text-center ${index === 0 ? "border-white/10" : "border-black/5"}`}><div><strong className="block text-xl">{number.format(expert.open)}</strong><span className={`text-[7px] ${index === 0 ? "text-white/35" : "text-black/35"}`}>پرونده باز</span></div><div><strong className="block text-xl">{number.format(expert.won)}</strong><span className={`text-[7px] ${index === 0 ? "text-white/35" : "text-black/35"}`}>فروش</span></div><div><strong className="block text-xl">{number.format(closeRate)}٪</strong><span className={`text-[7px] ${index === 0 ? "text-white/35" : "text-black/35"}`}>نرخ بستن</span></div></div>
            </article>
          );
        })}
      </div>

      <section className="mt-5 rounded-[22px] border border-black/[0.055] bg-white p-5">
        <span className="text-[8px] tracking-[0.16em] text-black/35">WORKFLOW</span><h2 className="mt-1 text-lg font-bold">قاعده پیشنهادی تخصیص</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3"><div className="rounded-2xl bg-[#f4f1eb] p-4"><strong className="text-[10px]">۱. درخواست جدید</strong><p className="mt-2 text-[9px] leading-6 text-black/45">تا وقتی تخصیص داده نشده در صف مشترک کارشناسان دیده می‌شود.</p></div><div className="rounded-2xl bg-[#f4f1eb] p-4"><strong className="text-[10px]">۲. Claim یا تخصیص مدیر</strong><p className="mt-2 text-[9px] leading-6 text-black/45">بعد از مالک شدن، فقط همان کارشناس وضعیت و یادداشت را جلو می‌برد.</p></div><div className="rounded-2xl bg-[#f4f1eb] p-4"><strong className="text-[10px]">۳. نتیجه نهایی</strong><p className="mt-2 text-[9px] leading-6 text-black/45">Won و Lost از کارهای باز خارج می‌شوند و در گزارش عملکرد می‌مانند.</p></div></div>
      </section>
    </PanelShell>
  );
}
