import { getTour } from "@/lib/api";
import { submitReservation } from "./actions";

const money = new Intl.NumberFormat("fa-IR");

export const dynamic = "force-dynamic";
type Params = Promise<{ tourId?: string; error?: string }>;

export default async function ReservePage({ searchParams }: { searchParams: Params }) {
  const query = await searchParams;
  const tour = query.tourId ? await getTour(query.tourId) : null;
  const isConsultation = !tour;

  return (
    <main className="min-h-screen bg-[#f3f0ea] px-3 py-4 sm:px-5 sm:py-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-4 flex items-center justify-between gap-4">
          <a href="/" className="brand-lockup leading-none" aria-label="بازگشت به صفحه اصلی">
            <span className="brand-dot" aria-hidden="true">S</span>
            <span>
              <strong className="block text-[10px] tracking-[0.22em]">SAFAROIRANIAN</strong>
              <small className="mt-1 block text-[8px] text-black/40">سفرو ایرانیان</small>
            </span>
          </a>
          <a href="/" className="inline-flex min-h-10 items-center rounded-full bg-white px-4 text-[9px] font-bold text-black/55 transition hover:text-black">→ بازگشت به تورها</a>
        </div>

        <div className="grid overflow-hidden rounded-[28px] border border-black/[0.06] bg-white shadow-[0_20px_70px_rgba(29,25,20,0.06)] lg:grid-cols-[0.92fr_1.08fr]">
          <aside className="reservation-summary bg-[#171715] p-6 text-white sm:p-8 lg:p-10">
            <span className="text-[9px] tracking-[0.2em] text-white/35">YOUR REQUEST</span>
            <h1 className="mt-3 text-3xl font-bold leading-tight tracking-[-0.04em] sm:text-4xl">
              {isConsultation ? "تور مناسب را با هم پیدا کنیم." : "یک مرحله تا ثبت درخواست."}
            </h1>
            <p className="mt-3 max-w-md text-[10px] leading-6 text-white/45">
              {isConsultation
                ? "شماره موبایل را ثبت کن؛ کارشناس برای انتخاب مقصد و تور مناسب با شما هماهنگ می‌شود."
                : "نیازی به ساخت حساب یا تکمیل فرم طولانی نیست؛ اطلاعات اصلی بعد از تماس تکمیل می‌شود."}
            </p>

            {tour && (
              <div className="mt-8 rounded-[20px] border border-white/10 bg-white/[0.045] p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <span className="text-[8px] text-white/35">تور انتخابی</span>
                    <strong className="mt-1 block text-sm">{tour.title}</strong>
                    <span className="mt-2 block text-[9px] leading-5 text-white/45">{tour.meta}</span>
                  </div>
                  <span className="rounded-full bg-white/10 px-2.5 py-1 text-[8px] text-white/70">{tour.tag}</span>
                </div>

                <div className="mt-4 flex flex-wrap gap-1.5">
                  {tour.services.split("·").slice(0, 3).map((service) => (
                    <span key={service} className="rounded-full border border-white/10 px-2.5 py-1 text-[8px] text-white/45">{service.trim()}</span>
                  ))}
                </div>

                <div className="mt-5 border-t border-white/10 pt-4">
                  <span className="block text-[8px] text-white/35">{tour.price ? "شروع قیمت / هر نفر" : "قیمت"}</span>
                  <div className="mt-1 flex items-baseline gap-2">
                    <strong className="text-xl">{tour.price ? money.format(tour.price) : "استعلام"}</strong>
                    {tour.price && <span className="text-[8px] text-white/35">تومان</span>}
                  </div>
                </div>
              </div>
            )}

            <div className="mt-8 grid grid-cols-3 gap-2" aria-label="مراحل ثبت درخواست">
              <div className="reservation-step done"><b>۱</b><span>انتخاب</span></div>
              <div className="reservation-step current"><b>۲</b><span>شماره</span></div>
              <div className="reservation-step"><b>۳</b><span>تماس</span></div>
            </div>
          </aside>

          <section className="p-6 sm:p-8 lg:p-10">
            <span className="text-[9px] tracking-[0.2em] text-black/35">FAST REQUEST</span>
            <h2 className="mt-2 text-2xl font-bold tracking-[-0.04em] sm:text-3xl">شماره موبایل شما</h2>
            <p className="mt-2 max-w-lg text-[10px] leading-6 text-black/45">
              درخواست اولیه رایگان است و در این مرحله پرداختی انجام نمی‌شود.
            </p>

            {query.error === "phone" && (
              <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[10px] text-red-700">
                شماره موبایل را به شکل 09xxxxxxxxx وارد کنید.
              </div>
            )}

            <form action={submitReservation} className="mt-7">
              <input type="hidden" name="tourId" value={tour?.id ?? "consultation"} />
              <label className="block">
                <span className="mb-2 block text-[10px] font-bold text-black/65">شماره موبایل</span>
                <div className="phone-field flex min-h-14 items-center rounded-[14px] border border-black/10 bg-[#fbfaf7] px-4 transition focus-within:border-black/35 focus-within:bg-white focus-within:ring-4 focus-within:ring-black/[0.035]">
                  <span className="ml-3 border-l border-black/10 pl-3 text-[10px] text-black/35">+98</span>
                  <input
                    name="phone"
                    inputMode="tel"
                    autoComplete="tel"
                    maxLength={11}
                    pattern="09[0-9]{9}"
                    placeholder="09xxxxxxxxx"
                    required
                    className="min-w-0 flex-1 bg-transparent text-left text-sm font-bold outline-none placeholder:text-black/25"
                    dir="ltr"
                    aria-describedby="phone-help"
                  />
                </div>
                <span id="phone-help" className="mt-2 block text-[8px] leading-5 text-black/35">مثال: 09123456789 · فقط برای هماهنگی همین درخواست</span>
              </label>

              <button className="mt-6 inline-flex min-h-13 w-full items-center justify-center rounded-[14px] bg-[#171715] px-5 text-[11px] font-bold text-white transition hover:bg-black focus:outline-none focus:ring-4 focus:ring-black/10" type="submit">
                {isConsultation ? "ثبت درخواست مشاوره" : "ثبت درخواست رزرو"}
                <span className="mr-2 text-base" aria-hidden="true">←</span>
              </button>
            </form>

            <div className="mt-5 flex items-center justify-center gap-2 text-[8px] text-black/35">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
              بدون پرداخت · بدون ساخت حساب · کمتر از یک دقیقه
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
