import type { Tour } from "@/types/tour";

const money = new Intl.NumberFormat("fa-IR");

function splitMeta(meta: string) {
  return meta.split("·").map((item) => item.trim()).filter(Boolean);
}

export function TourCard({ tour }: { tour: Tour }) {
  const meta = splitMeta(tour.meta);
  const services = tour.services.split("·").map((item) => item.trim()).filter(Boolean).slice(0, 3);

  return (
    <article className="tour-card group overflow-hidden rounded-[22px] border border-black/[0.07] bg-white transition duration-300 hover:-translate-y-1 hover:border-black/[0.12] hover:shadow-[0_18px_55px_rgba(28,25,20,0.09)]">
      <div data-city={tour.city} className="city-surface relative aspect-[1.55/1] overflow-hidden p-4 text-white">
        <div className="city-noise" aria-hidden="true" />
        <div className="relative z-10 flex items-start justify-between gap-3">
          <span className="rounded-full border border-white/15 bg-white/90 px-2.5 py-1 text-[8px] font-bold text-black backdrop-blur-sm">{tour.tag}</span>
          <span className="rounded-full border border-white/20 bg-black/10 px-2.5 py-1 text-[8px] text-white/80 backdrop-blur-sm">
            {tour.kind === "domestic" ? "داخلی" : "خارجی"}
          </span>
        </div>

        <span className="city-monogram" aria-hidden="true">{tour.cityLabel.slice(0, 1)}</span>

        <div className="absolute inset-x-4 bottom-4 z-10 flex items-end justify-between gap-4">
          <div>
            <span className="block text-[9px] tracking-[0.18em] text-white/55">DESTINATION</span>
            <strong className="mt-1 block text-[26px] leading-none">{tour.cityLabel}</strong>
          </div>
          {tour.price && (
            <span className="rounded-full bg-black/20 px-3 py-1.5 text-[9px] font-bold backdrop-blur-md">ظرفیت فعال</span>
          )}
        </div>
      </div>

      <div className="p-4 sm:p-[18px]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <a href={`/reserve?tourId=${encodeURIComponent(tour.id)}`} className="focus-ring block rounded-md">
              <h3 className="truncate text-[14px] font-bold leading-6 text-[#171715] transition group-hover:text-black">{tour.title}</h3>
            </a>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[9px] text-black/45">
              {meta.slice(0, 3).map((item, index) => (
                <span key={`${item}-${index}`} className="inline-flex items-center gap-2">
                  {index > 0 && <i className="h-1 w-1 rounded-full bg-black/20" aria-hidden="true" />}
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex min-h-7 flex-wrap gap-1.5">
          {services.map((service) => (
            <span key={service} className="rounded-full bg-[#f5f2ec] px-2.5 py-1.5 text-[8px] text-black/55">
              {service}
            </span>
          ))}
        </div>

        <div className="mt-4 flex items-end justify-between gap-3 border-t border-black/[0.06] pt-4">
          <div>
            <span className="block text-[8px] text-black/38">
              {tour.price ? "شروع قیمت برای هر نفر" : "قیمت بر اساس تاریخ و ظرفیت"}
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <strong className="text-[17px] font-bold tracking-tight">
                {tour.price ? money.format(tour.price) : "استعلام قیمت"}
              </strong>
              {tour.price && <span className="text-[8px] text-black/42">تومان</span>}
            </div>
          </div>

          <a
            href={`/reserve?tourId=${encodeURIComponent(tour.id)}`}
            className="focus-ring inline-flex min-h-11 shrink-0 items-center justify-center rounded-[13px] bg-[#171715] px-4 text-[10px] font-bold text-white transition hover:bg-black"
          >
            {tour.price ? "انتخاب تور" : "استعلام"}
            <span className="mr-2 text-sm" aria-hidden="true">←</span>
          </a>
        </div>
      </div>
    </article>
  );
}
