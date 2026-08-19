import type { Continent } from "@/types/tour";

const items: Array<{ key: Continent; label: string; note: string; index: string }> = [
  { key: "iran", label: "ایران", note: "کیش، مشهد، قشم، چابهار", index: "01" },
  { key: "asia", label: "آسیا", note: "ترکیه، خلیج فارس و شرق آسیا", index: "02" },
  { key: "europe", label: "اروپا", note: "روسیه و مسیرهای اروپایی", index: "03" },
  { key: "africa", label: "آفریقا", note: "تونس و مدیترانه", index: "04" },
  { key: "south-america", label: "آمریکای جنوبی", note: "سفرهای دور و خاص", index: "05" },
];

export function ContinentNav({ current }: { current?: Continent }) {
  return (
    <section id="destinations" className="bg-[#151513] px-4 py-16 text-white lg:px-8 lg:py-20">
      <div className="mx-auto max-w-[1480px]">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="text-[9px] tracking-[0.2em] text-white/35">DESTINATIONS</span>
            <h2 className="mt-2 text-4xl font-bold tracking-[-0.04em] md:text-6xl">از قاره شروع کن.</h2>
          </div>
          <p className="max-w-md text-[11px] leading-6 text-white/42">
            اگر مقصد دقیق را نمی‌دانی، قاره را انتخاب کن؛ فقط تورهای همان منطقه نمایش داده می‌شوند.
          </p>
        </div>

        <div className="continent-scroller -mx-4 flex snap-x gap-2 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 lg:grid-cols-5">
          {items.map((item) => (
            <a
              key={item.key}
              href={`/?continent=${item.key}#results`}
              aria-current={current === item.key ? "page" : undefined}
              className="continent-pill group min-w-[230px] snap-start rounded-[20px] border border-white/10 bg-white/[0.035] p-4 transition duration-200 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] sm:min-w-0"
            >
              <div className="flex items-start justify-between gap-4">
                <span className="text-[9px] text-white/30">{item.index}</span>
                <span className="text-lg text-white/25 transition group-hover:text-white/70" aria-hidden="true">↙</span>
              </div>
              <strong className="mt-8 block text-[15px]">{item.label}</strong>
              <span className="mt-1.5 block text-[9px] leading-5 text-white/38">{item.note}</span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
