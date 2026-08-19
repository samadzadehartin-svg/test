import { ContinentNav } from "@/components/continent-nav";
import { HeaderFilter } from "@/components/header-filter";
import { TourCard } from "@/components/tour-card";
import { getTours } from "@/lib/api";
import type { Budget, Continent, Tour, TourFilters, TripType } from "@/types/tour";

export const dynamic = "force-dynamic";
type PageSearchParams = Promise<{
  continent?: string;
  tripType?: string;
  budget?: string;
  view?: string;
}>;

const validContinents = new Set(["iran", "asia", "europe", "africa", "south-america"]);
const validTripTypes = new Set(["domestic", "international"]);
const validBudgets = new Set(["low", "mid", "high"]);

const featuredIds = [
  "istanbul-cartoon",
  "van-tamara",
  "kish-sadaf",
  "armenia-primer",
  "oman-carnelian",
  "antalya-nirvana",
];

const continentLabels: Record<Continent, string> = {
  iran: "ایران",
  asia: "آسیا",
  europe: "اروپا",
  africa: "آفریقا",
  "south-america": "آمریکای جنوبی",
};

const tripTypeLabels: Record<TripType, string> = {
  domestic: "داخلی",
  international: "خارجی",
};

const budgetLabels: Record<Budget, string> = {
  low: "تا ۳۰ میلیون",
  mid: "۳۰ تا ۷۰ میلیون",
  high: "بیشتر از ۷۰ میلیون",
};

function filterHref(filters: TourFilters, remove: keyof TourFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (key !== remove && value) params.set(key, value);
  });
  const query = params.toString();
  return `${query ? `/?${query}` : "/"}#results`;
}

function curatedTours(allTours: Tour[]) {
  const selected = featuredIds
    .map((id) => allTours.find((tour) => tour.id === id))
    .filter((tour): tour is Tour => Boolean(tour));

  if (selected.length >= 6) return selected;

  const fallback = allTours.filter((tour) => tour.price && !selected.some((item) => item.id === tour.id));
  return [...selected, ...fallback].slice(0, 6);
}

export default async function Home({ searchParams }: { searchParams: PageSearchParams }) {
  const query = await searchParams;

  const filters: TourFilters = {
    continent: validContinents.has(query.continent ?? "") ? (query.continent as Continent) : undefined,
    tripType: validTripTypes.has(query.tripType ?? "") ? (query.tripType as TripType) : undefined,
    budget: validBudgets.has(query.budget ?? "") ? (query.budget as Budget) : undefined,
  };

  const hasFilter = Boolean(filters.continent || filters.tripType || filters.budget);
  const showAll = query.view === "all";

  const allData = await getTours();
  const filteredData = hasFilter ? await getTours(filters) : allData;
  const items = hasFilter ? filteredData.items : showAll ? allData.items : curatedTours(allData.items);

  const resultTitle = hasFilter
    ? "تورهای مناسب انتخاب شما"
    : showAll
      ? "همه تورها"
      : "انتخاب‌های پیشنهادی امروز";

  return (
    <>
      <HeaderFilter defaults={filters} />

      <main>
        <section id="results" className="mx-auto max-w-[1480px] scroll-mt-40 px-4 py-10 sm:px-5 md:py-14 lg:px-8 lg:py-16">
          <div className="mb-6 flex flex-col gap-5 lg:mb-8 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="flex items-center gap-2 text-[9px] tracking-[0.18em] text-black/35">
                <span className="h-px w-7 bg-black/20" aria-hidden="true" />
                {hasFilter ? "MATCHED FOR YOU" : showAll ? "ALL TOURS" : "CURATED TODAY"}
              </div>
              <h1 className="mt-3 max-w-3xl text-[34px] font-bold leading-[1.15] tracking-[-0.04em] sm:text-4xl md:text-5xl lg:text-[58px]">
                {resultTitle}
              </h1>
              <p className="mt-3 max-w-xl text-[11px] leading-6 text-black/45 md:text-xs">
                {hasFilter
                  ? `${filteredData.count.toLocaleString("fa-IR")} تور مطابق فیلتر شما پیدا شد. برای رزرو فقط یک شماره موبایل نیاز داریم.`
                  : "فقط چند گزینه با ارزش خرید بهتر نمایش می‌دهیم تا انتخاب سریع بماند؛ برای دیدن جزئیات روی هر تور بزن."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 lg:justify-end">
              {filters.continent && (
                <a href={filterHref(filters, "continent")} className="active-filter-chip">
                  قاره: {continentLabels[filters.continent]} <span>×</span>
                </a>
              )}
              {filters.tripType && (
                <a href={filterHref(filters, "tripType")} className="active-filter-chip">
                  سفر: {tripTypeLabels[filters.tripType]} <span>×</span>
                </a>
              )}
              {filters.budget && (
                <a href={filterHref(filters, "budget")} className="active-filter-chip">
                  بودجه: {budgetLabels[filters.budget]} <span>×</span>
                </a>
              )}
              {hasFilter && (
                <a href="/#results" className="inline-flex min-h-9 items-center px-2 text-[9px] font-bold text-black/40 transition hover:text-black">
                  پاک کردن همه
                </a>
              )}
            </div>
          </div>

          {items.length ? (
            <div className="grid gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-3">
              {items.map((tour) => <TourCard key={tour.id} tour={tour} />)}
            </div>
          ) : (
            <div className="rounded-[24px] border border-dashed border-black/15 bg-white px-5 py-16 text-center md:py-24">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[#f2eee7] text-lg" aria-hidden="true">⌕</span>
              <strong className="mt-4 block text-lg">با این فیلتر توری پیدا نشد.</strong>
              <p className="mx-auto mt-2 max-w-md text-[10px] leading-6 text-black/45">بودجه یا قاره را تغییر بده تا گزینه‌های بیشتری ببینی.</p>
              <a href="/#results" className="mt-5 inline-flex min-h-10 items-center rounded-full bg-[#171715] px-5 text-[10px] font-bold text-white">پاک کردن فیلترها</a>
            </div>
          )}

          {!hasFilter && !showAll && (
            <div className="mt-7 flex flex-col items-center justify-center gap-2 text-center">
              <a href="/?view=all#results" className="inline-flex min-h-11 items-center rounded-full border border-black/10 bg-white px-5 text-[10px] font-bold transition hover:border-black/20 hover:bg-[#f5f2ec]">
                مشاهده همه {allData.count.toLocaleString("fa-IR")} تور
                <span className="mr-2" aria-hidden="true">←</span>
              </a>
              <span className="text-[8px] text-black/35">یا با فیلتر بالا سریع‌تر گزینه مناسب را پیدا کن.</span>
            </div>
          )}
        </section>

        <ContinentNav current={filters.continent} />

        <section className="px-3 py-3 sm:px-5 lg:px-8">
          <div className="mx-auto flex max-w-[1480px] flex-col gap-6 overflow-hidden rounded-[26px] bg-[#eee8dc] px-5 py-8 sm:px-8 md:flex-row md:items-center md:justify-between lg:px-12 lg:py-10">
            <div>
              <span className="text-[9px] tracking-[0.18em] text-black/35">NEED HELP?</span>
              <h2 className="mt-2 text-2xl font-bold tracking-[-0.04em] sm:text-3xl">بین چند تور مرددی؟</h2>
              <p className="mt-2 max-w-xl text-[10px] leading-6 text-black/48">شماره‌ات را ثبت کن؛ انتخاب‌های نامناسب را حذف می‌کنیم و چند گزینه نزدیک به بودجه‌ات می‌ماند.</p>
            </div>
            <a href="/reserve" className="inline-flex min-h-12 shrink-0 items-center justify-center rounded-[14px] bg-[#171715] px-6 text-[10px] font-bold text-white transition hover:bg-black">
              مشاوره انتخاب تور
              <span className="mr-2 text-base" aria-hidden="true">←</span>
            </a>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-[1480px] flex-col gap-3 px-4 py-9 text-[9px] text-black/38 sm:px-5 md:flex-row md:items-center md:justify-between lg:px-8">
        <div>
          <strong className="block tracking-[0.2em] text-black/65">SAFAROIRANIAN</strong>
          <span className="mt-1 block">انتخاب و درخواست رزرو تور</span>
        </div>
        <div className="flex gap-5">
          <a href="#destinations" className="transition hover:text-black">مقصدها</a>
          <a href="/reserve" className="transition hover:text-black">مشاوره</a>
          <a href="/staff/login" className="transition hover:text-black">ورود کارکنان</a>
          <span>© 2026</span>
        </div>
      </footer>
    </>
  );
}
