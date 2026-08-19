type Params = Promise<{ ref?: string }>;

export default async function SuccessPage({ searchParams }: { searchParams: Params }) {
  const query = await searchParams;
  const shortRef = query.ref?.slice(0, 8).toUpperCase();

  return (
    <main className="grid min-h-screen place-items-center bg-[#f3f0ea] px-4 py-8">
      <section className="w-full max-w-lg overflow-hidden rounded-[28px] border border-black/[0.06] bg-white shadow-[0_20px_70px_rgba(29,25,20,0.06)]">
        <div className="bg-[#171715] px-7 py-8 text-white sm:px-9">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-[#eee8dc] text-2xl font-bold text-[#171715]">✓</div>
          <span className="mt-6 block text-[9px] tracking-[0.2em] text-white/35">REQUEST RECEIVED</span>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.04em]">درخواست شما ثبت شد.</h1>
          {shortRef && <span className="mt-3 inline-block rounded-full border border-white/10 px-3 py-1.5 text-[8px] text-white/45">کد پیگیری: {shortRef}</span>}
        </div>

        <div className="p-7 sm:p-9">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="success-step"><b>۱</b><span>درخواست دریافت شد</span></div>
            <div className="success-step"><b>۲</b><span>بررسی ظرفیت و قیمت</span></div>
            <div className="success-step"><b>۳</b><span>تماس برای نهایی‌سازی</span></div>
          </div>

          <p className="mt-6 text-[10px] leading-6 text-black/45">در نسخه نهایی، این درخواست مستقیم وارد CRM فروش می‌شود و کارشناس با شماره ثبت‌شده تماس می‌گیرد.</p>
          <a href="/" className="mt-6 inline-flex min-h-12 w-full items-center justify-center rounded-[14px] bg-[#171715] px-6 text-[10px] font-bold text-white transition hover:bg-black">بازگشت به صفحه اصلی</a>
        </div>
      </section>
    </main>
  );
}
