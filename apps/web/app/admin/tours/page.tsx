import { updateTourAction } from "@/app/staff/actions";
import { PanelShell } from "@/components/panel/panel-shell";
import { getManagedTours } from "@/lib/staff-api";
import { requireStaffRole } from "@/lib/staff-auth";

const money = new Intl.NumberFormat("fa-IR");
type Params = Promise<{ q?: string }>;

export default async function AdminToursPage({ searchParams }: { searchParams: Params }) {
  const user = await requireStaffRole("admin");
  const query = await searchParams;
  const tours = await getManagedTours();
  const q = query.q?.trim().toLowerCase() ?? "";
  const filtered = q ? tours.filter((tour) => [tour.title, tour.cityLabel, tour.hotel, tour.tag].join(" ").toLowerCase().includes(q)) : tours;

  return (
    <PanelShell user={user} current="/admin/tours" title="مدیریت تورها" subtitle="قیمت، برچسب و وضعیت انتشار را بدون ورود به صفحه‌های متعدد تغییر بده. تغییرات روی API عمومی تورها اثر می‌گذارد.">
      <form method="get" className="mb-5 flex max-w-xl gap-2">
        <input name="q" defaultValue={query.q} className="input input-bordered h-11 flex-1 rounded-xl bg-white text-[10px]" placeholder="جستجوی مقصد، هتل یا نام تور…" />
        <button className="btn h-11 rounded-xl border-0 bg-[#171715] px-5 text-[9px] text-white">جستجو</button>
      </form>

      <div className="grid gap-3 xl:grid-cols-2">
        {filtered.map((tour) => (
          <details key={tour.id} className="group overflow-hidden rounded-[20px] border border-black/[0.055] bg-white">
            <summary className="grid cursor-pointer list-none grid-cols-[1fr_auto] gap-4 p-4 sm:p-5">
              <div className="min-w-0"><span className="text-[8px] font-bold text-black/35">{tour.cityLabel} · {tour.tag}</span><strong className="mt-1 block truncate text-[11px]">{tour.title}</strong><span className="mt-1 block truncate text-[8px] text-black/38">{tour.meta}</span></div>
              <div className="text-left"><span className={`inline-flex rounded-full px-2 py-1 text-[7px] font-bold ${tour.active ? "bg-emerald-50 text-emerald-700" : "bg-black/5 text-black/40"}`}>{tour.active ? "فعال" : "غیرفعال"}</span><strong className="mt-2 block text-[11px]">{tour.price ? money.format(tour.price) : "استعلام"}</strong></div>
            </summary>
            <form action={updateTourAction} className="grid gap-4 border-t border-black/[0.055] bg-[#faf8f4] p-4 sm:grid-cols-2 lg:grid-cols-[1fr_.7fr_auto] lg:items-end">
              <input type="hidden" name="id" value={tour.id} />
              <label><span className="mb-2 block text-[8px] font-bold text-black/45">قیمت / تومان</span><input name="price" defaultValue={tour.price ?? ""} inputMode="numeric" className="input input-bordered h-11 w-full rounded-xl bg-white text-[10px]" placeholder="خالی = استعلام قیمت" dir="ltr" /></label>
              <label><span className="mb-2 block text-[8px] font-bold text-black/45">برچسب</span><input name="tag" defaultValue={tour.tag} className="input input-bordered h-11 w-full rounded-xl bg-white text-[10px]" /></label>
              <div className="flex items-center gap-3 lg:pb-1"><label className="flex items-center gap-2 text-[9px] font-bold"><input type="checkbox" name="active" defaultChecked={tour.active} className="toggle toggle-sm" /> انتشار</label><button className="btn h-11 rounded-xl border-0 bg-[#171715] px-5 text-[9px] text-white">ذخیره</button></div>
            </form>
          </details>
        ))}
      </div>
    </PanelShell>
  );
}
