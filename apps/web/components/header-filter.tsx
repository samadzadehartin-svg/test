import type { TourFilters } from "@/types/tour";

const continentOptions = [
  ["iran", "ایران"],
  ["asia", "آسیا"],
  ["europe", "اروپا"],
  ["africa", "آفریقا"],
  ["south-america", "آمریکای جنوبی"],
] as const;

export function HeaderFilter({ defaults }: { defaults: TourFilters }) {
  const hasFilters = Boolean(defaults.continent || defaults.tripType || defaults.budget);

  return (
    <header className="site-header sticky top-0 z-50 border-b border-black/[0.06] bg-[#fbfaf7]/95 backdrop-blur-xl">
      <div className="mx-auto max-w-[1480px] px-3 py-3 sm:px-5 lg:px-8">
        <div className="flex items-center justify-between gap-4">
          <a href="/" className="brand-lockup shrink-0 leading-none" aria-label="SafaroIranian - صفحه اصلی">
            <span className="brand-dot" aria-hidden="true">S</span>
            <span>
              <strong className="block text-[11px] tracking-[0.24em]">SAFAROIRANIAN</strong>
              <small className="mt-1 block text-[8px] text-black/40">سفرو ایرانیان</small>
            </span>
          </a>

          <div className="hidden items-center gap-2 lg:flex">
            <a href="#destinations" className="header-link">مقصدها</a>
            <a href="/?continent=asia#results" className="header-link">تورهای خارجی</a>
            <a href="/?continent=iran#results" className="header-link">تورهای داخلی</a>
          </div>

          <a
            href="/reserve"
            className="hidden min-h-10 shrink-0 items-center rounded-full border border-black/10 bg-white px-4 text-[10px] font-bold transition hover:border-black/20 hover:bg-[#f3f0ea] sm:inline-flex"
          >
            درخواست مشاوره
          </a>
        </div>

        <form action="/" method="get" className="search-dock mt-3 grid overflow-hidden rounded-[18px] border border-black/[0.08] bg-white shadow-[0_8px_30px_rgba(22,20,17,0.05)] md:grid-cols-[1.1fr_1fr_1fr_auto]">
          <label className="filter-cell">
            <span className="filter-kicker">قاره</span>
            <span className="filter-row">
              <span className="filter-icon" aria-hidden="true">⌖</span>
              <select
                name="continent"
                defaultValue={defaults.continent ?? ""}
                className="select select-ghost h-8 min-h-0 w-full px-0 text-[12px] font-bold focus:bg-transparent focus:outline-none"
                aria-label="انتخاب قاره"
              >
                <option value="">هر قاره‌ای</option>
                {continentOptions.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </span>
          </label>

          <label className="filter-cell">
            <span className="filter-kicker">نوع سفر</span>
            <span className="filter-row">
              <span className="filter-icon" aria-hidden="true">↗</span>
              <select
                name="tripType"
                defaultValue={defaults.tripType ?? ""}
                className="select select-ghost h-8 min-h-0 w-full px-0 text-[12px] font-bold focus:bg-transparent focus:outline-none"
                aria-label="انتخاب نوع سفر"
              >
                <option value="">فرقی ندارد</option>
                <option value="domestic">داخلی</option>
                <option value="international">خارجی</option>
              </select>
            </span>
          </label>

          <label className="filter-cell">
            <span className="filter-kicker">بودجه هر نفر</span>
            <span className="filter-row">
              <span className="filter-icon" aria-hidden="true">◌</span>
              <select
                name="budget"
                defaultValue={defaults.budget ?? ""}
                className="select select-ghost h-8 min-h-0 w-full px-0 text-[12px] font-bold focus:bg-transparent focus:outline-none"
                aria-label="انتخاب بودجه"
              >
                <option value="">هر بودجه‌ای</option>
                <option value="low">تا ۳۰ میلیون</option>
                <option value="mid">۳۰ تا ۷۰ میلیون</option>
                <option value="high">بیشتر از ۷۰ میلیون</option>
              </select>
            </span>
          </label>

          <div className="flex min-h-14 items-stretch gap-1 bg-[#f7f4ee] p-1.5 md:min-w-[136px]">
            {hasFilters && (
              <a href="/#results" className="grid min-w-11 place-items-center rounded-xl text-sm text-black/45 transition hover:bg-white hover:text-black" aria-label="پاک کردن فیلترها">
                ×
              </a>
            )}
            <button className="btn h-auto min-h-11 flex-1 rounded-xl border-0 bg-[#171715] px-5 text-[11px] font-bold text-white shadow-none hover:bg-black" type="submit">
              نمایش تورها
            </button>
          </div>
        </form>
      </div>
    </header>
  );
}
