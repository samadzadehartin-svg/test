import { getStaffUser } from "@/lib/staff-api";
import { redirect } from "next/navigation";
import { loginAction } from "../actions";

type Params = Promise<{ error?: string }>;

export default async function StaffLogin({ searchParams }: { searchParams: Params }) {
  const user = await getStaffUser();
  if (user) redirect(user.role === "admin" ? "/admin" : "/expert");
  const query = await searchParams;

  return (
    <main className="min-h-screen bg-[#11110f] px-4 py-8 text-[#171715] sm:grid sm:place-items-center">
      <section className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-[30px] bg-[#fbfaf7] shadow-2xl sm:grid-cols-[0.9fr_1.1fr]">
        <div className="relative hidden min-h-[640px] overflow-hidden bg-[#1b2421] p-10 text-white sm:block">
          <div className="absolute -left-24 -top-20 h-72 w-72 rounded-full border border-white/10" />
          <div className="absolute -left-10 top-16 h-72 w-72 rounded-full border border-white/5" />
          <div className="relative z-10 flex h-full flex-col justify-between">
            <div>
              <div className="grid h-11 w-11 place-items-center rounded-full border border-white/20 font-serif">S</div>
              <p className="mt-5 text-[9px] tracking-[0.24em] text-white/45">SAFAROIRANIAN OFFICE</p>
            </div>
            <div>
              <h1 className="max-w-sm text-4xl font-bold leading-[1.25] tracking-[-0.04em]">فروش تور، بدون شلوغی پنل‌های قدیمی.</h1>
              <p className="mt-4 max-w-sm text-[11px] leading-7 text-white/48">درخواست‌ها، تورها و کارهای روزانه در یک محیط سریع و نقش‌محور.</p>
            </div>
          </div>
        </div>

        <div className="p-6 sm:p-10 lg:p-14">
          <a href="/" className="text-[10px] font-bold text-black/40 transition hover:text-black">→ برگشت به سایت</a>
          <div className="mt-16 sm:mt-24">
            <span className="text-[9px] tracking-[0.2em] text-black/35">STAFF SIGN IN</span>
            <h2 className="mt-3 text-3xl font-bold tracking-[-0.04em]">ورود به پنل</h2>
            <p className="mt-2 text-[10px] leading-6 text-black/45">بر اساس حساب شما، پنل مدیر یا کارشناس باز می‌شود.</p>

            {query.error && <div className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-[10px] font-bold text-red-700">نام کاربری یا رمز عبور درست نیست.</div>}

            <form action={loginAction} className="mt-7 space-y-4">
              <label className="block">
                <span className="mb-2 block text-[9px] font-bold text-black/50">نام کاربری</span>
                <input name="username" required autoComplete="username" className="input input-bordered h-12 w-full rounded-xl bg-white text-sm" placeholder="admin یا expert" dir="ltr" />
              </label>
              <label className="block">
                <span className="mb-2 block text-[9px] font-bold text-black/50">رمز عبور</span>
                <input name="password" type="password" required autoComplete="current-password" className="input input-bordered h-12 w-full rounded-xl bg-white text-sm" placeholder="••••••••" dir="ltr" />
              </label>
              <button className="btn h-12 w-full rounded-xl border-0 bg-[#171715] text-xs text-white hover:bg-black">ورود امن</button>
            </form>

            <div className="mt-6 rounded-2xl bg-[#f1ede6] p-4 text-[9px] leading-6 text-black/50">
              <strong className="block text-black/65">حساب‌های دموی توسعه</strong>
              مدیر: <code dir="ltr">admin / admin123</code><br />
              کارشناس: <code dir="ltr">expert / expert123</code>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
