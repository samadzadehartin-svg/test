"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft, CalendarDays, ChevronLeft, Compass, Headphones, Heart,
  MapPin, Menu, Plane, Search, ShieldCheck, Sparkles, Star, UserRound,
  WandSparkles, X
} from "lucide-react";
import { Destination, fallbackDestinations, fallbackTours, Tour } from "@/lib/data";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000/api";

const formatPrice = (value: number) => new Intl.NumberFormat("fa-IR").format(value);

export default function HomePage() {
  const [destinations, setDestinations] = useState<Destination[]>(fallbackDestinations);
  const [tours, setTours] = useState<Tour[]>(fallbackTours);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [travelers, setTravelers] = useState("2");

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/destinations`).then((r) => (r.ok ? r.json() : Promise.reject())),
      fetch(`${API_URL}/tours`).then((r) => (r.ok ? r.json() : Promise.reject())),
    ])
      .then(([d, t]) => {
        setDestinations(d);
        setTours(t);
      })
      .catch(() => {
        // Backend is optional for the visual preview; fallback data keeps the page usable.
      });
  }, []);

  const searchSummary = useMemo(() => {
    if (!destination && !date) return "";
    return `${destination || "همه مقصدها"}${date ? ` • ${date}` : ""} • ${travelers} مسافر`;
  }, [destination, date, travelers]);

  return (
    <main className="min-h-screen overflow-hidden bg-[#05080a] text-white">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-black/55 backdrop-blur-2xl">
        <div className="container-shell flex h-20 items-center justify-between gap-6">
          <a href="#" className="flex items-center gap-3 font-black text-[#e6b96d]">
            <span className="grid size-11 place-items-center rounded-2xl border border-[#e6b96d]/30 bg-[#e6b96d]/10 shadow-[0_0_30px_rgba(230,185,109,.12)]"><Plane className="size-5 -rotate-45" /></span>
            <span><b className="block tracking-wide">SAFAR IRANIAN</b><small className="font-medium text-white/60">سفر ایرانیان</small></span>
          </a>

          <nav className="hidden items-center gap-7 text-sm text-white/70 lg:flex">
            {[
              ["تورها", "#tours"], ["مقاصد", "#destinations"], ["تور لحظه آخری", "#tours"],
              ["تور ساز", "#builder"], ["مجله سفر", "#mag"], ["درباره ما", "#why"]
            ].map(([label, href]) => <a key={label} href={href} className="transition hover:text-[#e6b96d]">{label}</a>)}
          </nav>

          <a href="tel:+982100000000" className="btn-gold hidden md:inline-flex"><Headphones className="size-4" /> مشاوره رایگان</a>
          <button onClick={() => setMobileOpen(true)} className="btn btn-ghost btn-square lg:hidden" aria-label="منو"><Menu /></button>
        </div>
      </header>

      {mobileOpen && (
        <div className="fixed inset-0 z-[70] bg-black/90 p-6 backdrop-blur-2xl lg:hidden">
          <div className="flex items-center justify-between"><span className="font-black text-[#e6b96d]">سفر ایرانیان</span><button className="btn btn-ghost btn-square" onClick={() => setMobileOpen(false)}><X /></button></div>
          <div className="mt-12 grid gap-2 text-xl">
            {["تورها", "مقاصد", "تور لحظه آخری", "تور ساز", "مجله سفر", "درباره ما"].map((x) => <a key={x} href="#" className="rounded-2xl p-4 hover:bg-white/5">{x}</a>)}
          </div>
        </div>
      )}

      <section className="hero-scene relative min-h-[820px] overflow-hidden pt-28">
        <video
          className="hero-video absolute inset-0 h-full w-full object-cover"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster="/videos/hero-istanbul-poster.jpg"
          aria-hidden="true"
        >
          <source src="/videos/hero-istanbul.mp4" type="video/mp4" />
        </video>
        <div className="hero-video-overlay absolute inset-0" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_68%_20%,rgba(230,185,109,.11),transparent_28%),linear-gradient(180deg,rgba(2,5,7,.06),#05080a_94%)]" />
        <div className="container-shell relative z-10 flex min-h-[690px] flex-col justify-center pt-8">
          <div className="max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#e6b96d]/25 bg-[#e6b96d]/10 px-4 py-2 text-sm text-[#f0ce93]"><Sparkles className="size-4" /> تجربه سفر، دقیقاً مطابق سلیقه شما</div>
            <h1 className="text-4xl font-black leading-[1.45] sm:text-6xl xl:text-7xl">سفر بعدی‌ات<br />از اینجا <span className="text-gold">شروع</span> می‌شود</h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-white/60 sm:text-lg">بهترین تورها، قیمت‌های رقابتی و تجربه‌ای متفاوت؛ از انتخاب مقصد تا برگشت به خانه کنارت هستیم.</p>
          </div>

          <div className="glass-panel mt-12 max-w-6xl p-3 sm:p-4">
            <div className="grid gap-3 lg:grid-cols-[1.2fr_1fr_.7fr_auto]">
              <label className="search-field"><span>مقصد</span><div><MapPin /><input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="مثلاً استانبول" /></div></label>
              <label className="search-field"><span>تاریخ سفر</span><div><CalendarDays /><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div></label>
              <label className="search-field"><span>تعداد مسافر</span><div><UserRound /><select value={travelers} onChange={(e) => setTravelers(e.target.value)}>{[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n} نفر</option>)}</select></div></label>
              <button className="btn-gold min-h-16 px-7"><Search className="size-5" /> پیدا کردن تور</button>
            </div>
          </div>
          {searchSummary && <p className="mt-3 text-sm text-white/40">جستجوی شما: {searchSummary}</p>}
          <div className="mt-5 flex flex-wrap gap-3"><a className="btn-outline-gold" href="#tours"><Plane className="size-4" /> مشاهده تورها</a><a className="btn-outline-gold" href="#builder"><WandSparkles className="size-4" /> تور دلخواه من</a></div>
        </div>
      </section>

      <section id="destinations" className="section-space container-shell">
        <SectionTitle title="مقاصد محبوب" subtitle="پرطرفدارترین انتخاب‌های مسافران سفر ایرانیان" />
        <div className="hide-scrollbar flex snap-x gap-4 overflow-x-auto pb-5">
          {destinations.map((item) => (
            <article key={item.id} className="destination-card group min-w-[185px] snap-start sm:min-w-[220px]">
              <img src={item.image} alt={item.name} />
              <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent" />
              <div className="absolute bottom-0 right-0 p-5"><h3 className="text-lg font-black">{item.name}</h3><p className="mt-1 flex items-center gap-1 text-xs text-[#e8bd78]"><MapPin className="size-3" />{item.country}</p></div>
            </article>
          ))}
        </div>
      </section>

      <section id="tours" className="section-space container-shell">
        <SectionTitle title="آفرهای امروز" subtitle="تورهای منتخب با ظرفیت محدود و قیمت ویژه" action="مشاهده همه آفرها" />
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {tours.map((tour) => <TourCard key={tour.id} tour={tour} />)}
        </div>
      </section>

      <section id="builder" className="section-space container-shell">
        <div className="builder-panel relative overflow-hidden rounded-[36px] border border-white/10 p-7 sm:p-10 lg:p-14">
          <div className="absolute -left-16 top-1/2 size-80 -translate-y-1/2 rounded-full bg-[#e6b96d]/10 blur-3xl" />
          <div className="relative grid items-center gap-12 lg:grid-cols-2">
            <div>
              <span className="eyebrow">تور اختصاصی</span><h2 className="mt-4 text-3xl font-black sm:text-5xl">تور ساز؛ سفر را خودت بچین</h2>
              <p className="mt-5 max-w-xl leading-8 text-white/60">مقصد، تاریخ، هتل و نوع پرواز را انتخاب کن؛ ما بهترین ترکیب ممکن را برای بودجه و سبک سفرت آماده می‌کنیم.</p>
              <button className="btn-gold mt-8"><WandSparkles className="size-5" /> شروع تور ساز <ArrowLeft className="size-4" /></button>
            </div>
            <div className="relative mx-auto grid size-72 place-items-center rounded-full border border-[#e6b96d]/20 bg-black/30 shadow-[0_0_80px_rgba(230,185,109,.14)] sm:size-96">
              <div className="absolute inset-7 rounded-full border border-dashed border-[#e6b96d]/25 animate-[spin_25s_linear_infinite]" />
              <div className="luggage">✈</div>
              <span className="orbit-icon left-2 top-1/2"><Plane /></span><span className="orbit-icon right-5 top-8"><CalendarDays /></span><span className="orbit-icon bottom-7 right-4"><MapPin /></span>
            </div>
          </div>
        </div>
      </section>

      <section id="why" className="section-space container-shell">
        <SectionTitle title="چرا سفر ایرانیان؟" subtitle="فقط تور نمی‌فروشیم؛ خیال راحت سفر را می‌سازیم" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <Feature icon={<Heart />} title="همراهی تا پایان سفر" text="پشتیبانی قبل، حین و بعد سفر" />
          <Feature icon={<ShieldCheck />} title="پرداخت امن" text="فرآیند شفاف و مطمئن" />
          <Feature icon={<Star />} title="بهترین قیمت" text="پیشنهادهای رقابتی و واقعی" />
          <Feature icon={<MapPin />} title="مشاوره تخصصی" text="انتخاب دقیق متناسب با نیاز" />
          <Feature icon={<Headphones />} title="پشتیبانی ۲۴/۷" text="در تمام مراحل سفر" />
        </div>
      </section>

      <section id="mag" className="section-space container-shell">
        <SectionTitle title="مجله سفر" subtitle="ایده، راهنما و تجربه برای سفر بهتر" action="همه مقالات" />
        <div className="grid gap-5 lg:grid-cols-3">
          <MagazineCard image="https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1000&q=80" title="چطور یک سفر خارجی اقتصادی اما باکیفیت داشته باشیم؟" />
          <MagazineCard image="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1000&q=80" title="بهترین زمان سفر به تایلند؛ از آب‌وهوا تا هزینه‌ها" />
          <MagazineCard image="https://images.unsplash.com/photo-1530789253388-582c481c54b0?auto=format&fit=crop&w=1000&q=80" title="۷ تجربه‌ای که در استانبول نباید از دست بدهید" />
        </div>
      </section>

      <section className="container-shell pb-24 pt-6">
        <div className="cta-panel flex flex-col items-start justify-between gap-7 rounded-[32px] p-7 sm:p-10 lg:flex-row lg:items-center">
          <div><span className="eyebrow">تصمیم سخت شده؟</span><h2 className="mt-3 text-3xl font-black">هنوز نمی‌دونی کجا بری؟</h2><p className="mt-3 text-white/60">بودجه و شرایطت را بگو؛ چند پیشنهاد مناسب برات پیدا می‌کنیم.</p></div>
          <button className="btn-gold shrink-0"><Headphones className="size-5" /> دریافت مشاوره رایگان</button>
        </div>
      </section>

      <footer className="border-t border-white/10 py-10"><div className="container-shell flex flex-col justify-between gap-4 text-sm text-white/40 sm:flex-row"><span>© سفر ایرانیان — تمامی حقوق محفوظ است.</span><span>طراحی نسخه جدید Safar Iranian</span></div></footer>
    </main>
  );
}

function SectionTitle({ title, subtitle, action }: { title: string; subtitle: string; action?: string }) {
  return <div className="mb-8 flex items-end justify-between gap-5"><div><span className="eyebrow">SAFAR IRANIAN</span><h2 className="mt-2 text-2xl font-black sm:text-3xl">{title}</h2><p className="mt-2 text-sm text-white/40">{subtitle}</p></div>{action && <button className="hidden items-center gap-2 text-sm text-white/50 hover:text-[#e6b96d] sm:flex">{action}<ChevronLeft className="size-4" /></button>}</div>;
}

function TourCard({ tour }: { tour: Tour }) {
  return <article className="tour-card group overflow-hidden rounded-[28px] border border-white/10 bg-white/[.035]">
    <div className="relative h-56 overflow-hidden"><img src={tour.image} alt={tour.title} className="h-full w-full object-cover transition duration-700 group-hover:scale-110" /><div className="absolute inset-0 bg-gradient-to-t from-[#080b0d] via-transparent to-transparent" />{tour.discount && <span className="absolute right-4 top-4 rounded-full bg-[#e6b96d] px-3 py-1 text-xs font-black text-[#17110a]">٪{tour.discount} تخفیف</span>}<div className="absolute bottom-4 right-5"><h3 className="text-2xl font-black">{tour.title}</h3><p className="text-xs text-[#e6b96d]">{tour.country}</p></div></div>
    <div className="p-5"><div className="mb-5 flex items-center gap-4 text-xs text-white/40"><span className="flex items-center gap-1"><CalendarDays className="size-4" />{tour.nights} شب و {tour.days} روز</span><span className="flex items-center gap-1"><Plane className="size-4" />پرواز رفت و برگشت</span></div>{tour.oldPrice && <div className="text-xs text-white/30 line-through">{formatPrice(tour.oldPrice)} تومان</div>}<div className="mt-1 text-xl font-black">{formatPrice(tour.price)} <small className="text-xs font-medium text-white/40">تومان</small></div><button className="btn-outline-gold mt-5 w-full justify-center">مشاهده و رزرو</button></div>
  </article>;
}

function Feature({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <article className="feature-card"><div className="grid size-12 place-items-center rounded-2xl border border-[#e6b96d]/20 bg-[#e6b96d]/10 text-[#e6b96d]">{icon}</div><div><h3 className="font-bold">{title}</h3><p className="mt-1 text-xs leading-6 text-white/40">{text}</p></div></article>;
}

function MagazineCard({ image, title }: { image: string; title: string }) {
  return <article className="group relative h-64 overflow-hidden rounded-[28px] border border-white/10"><img src={image} alt={title} className="h-full w-full object-cover transition duration-700 group-hover:scale-105" /><div className="absolute inset-0 bg-gradient-to-t from-black via-black/20 to-transparent" /><div className="absolute inset-x-0 bottom-0 p-6"><div className="mb-3 flex items-center gap-2 text-xs text-[#e6b96d]"><Compass className="size-4" /> راهنمای سفر</div><h3 className="font-bold leading-7">{title}</h3></div></article>;
}
