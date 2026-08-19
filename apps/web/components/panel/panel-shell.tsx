import type { ReactNode } from "react";
import type { StaffRole, StaffUser } from "@/types/staff";
import { logoutAction } from "@/app/staff/actions";

type NavItem = { href: string; label: string; icon: string };

const adminNav: NavItem[] = [
  { href: "/admin", label: "داشبورد", icon: "⌂" },
  { href: "/admin/leads", label: "درخواست‌ها", icon: "◎" },
  { href: "/admin/tours", label: "تورها", icon: "◇" },
  { href: "/admin/team", label: "کارشناسان", icon: "◌" },
];

const expertNav: NavItem[] = [
  { href: "/expert", label: "امروز", icon: "⌂" },
  { href: "/expert/leads", label: "درخواست‌ها", icon: "◎" },
];

export function PanelShell({
  user,
  current,
  title,
  subtitle,
  children,
}: {
  user: StaffUser;
  current: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const nav = user.role === "admin" ? adminNav : expertNav;
  const roleLabel = user.role === "admin" ? "مدیر سیستم" : "کارشناس فروش";

  return (
    <div className="min-h-screen bg-[#f4f1eb] text-[#171715]">
      <div className="mx-auto grid min-h-screen max-w-[1700px] lg:grid-cols-[230px_1fr]">
        <aside className="hidden border-l border-black/5 bg-[#191917] p-5 text-white lg:flex lg:flex-col">
          <a href="/" className="flex items-center gap-3 px-2 py-2">
            <span className="grid h-9 w-9 place-items-center rounded-full border border-white/18 font-serif text-sm">S</span>
            <span>
              <strong className="block text-[10px] tracking-[0.18em]">SAFAROIRANIAN</strong>
              <small className="mt-1 block text-[7px] text-white/35">OFFICE</small>
            </span>
          </a>

          <nav className="mt-12 space-y-1.5">
            {nav.map((item) => {
              const active = current === item.href;
              return (
                <a key={item.href} href={item.href} className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-[10px] font-bold transition ${active ? "bg-white text-[#171715]" : "text-white/48 hover:bg-white/[0.06] hover:text-white"}`}>
                  <span className={`grid h-7 w-7 place-items-center rounded-lg text-xs ${active ? "bg-[#eee8dc]" : "bg-white/[0.05]"}`}>{item.icon}</span>
                  {item.label}
                </a>
              );
            })}
          </nav>

          <div className="mt-auto rounded-2xl border border-white/8 bg-white/[0.035] p-4">
            <span className="text-[8px] text-white/35">حساب فعال</span>
            <strong className="mt-1 block text-[11px]">{user.name}</strong>
            <span className="mt-1 block text-[8px] text-white/35">{roleLabel}</span>
            <form action={logoutAction} className="mt-4">
              <button className="text-[9px] font-bold text-white/45 transition hover:text-white">خروج از پنل ←</button>
            </form>
          </div>
        </aside>

        <main className="min-w-0">
          <header className="sticky top-0 z-40 border-b border-black/5 bg-[#f4f1eb]/94 backdrop-blur-xl">
            <div className="flex min-h-[74px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
              <div>
                <span className="text-[8px] tracking-[0.18em] text-black/35">{user.role === "admin" ? "ADMIN PANEL" : "EXPERT WORKSPACE"}</span>
                <h1 className="mt-1 text-xl font-bold tracking-[-0.03em] sm:text-2xl">{title}</h1>
              </div>
              <div className="flex items-center gap-2">
                <a href="/" className="hidden min-h-9 items-center rounded-full border border-black/8 bg-white px-4 text-[9px] font-bold text-black/55 sm:inline-flex">مشاهده سایت ↗</a>
                <form action={logoutAction} className="lg:hidden">
                  <button className="grid h-9 w-9 place-items-center rounded-full border border-black/8 bg-white text-xs">↪</button>
                </form>
              </div>
            </div>
            <nav className="flex gap-1 overflow-x-auto border-t border-black/[0.035] px-4 py-2 lg:hidden">
              {nav.map((item) => (
                <a key={item.href} href={item.href} className={`shrink-0 rounded-full px-4 py-2 text-[9px] font-bold ${current === item.href ? "bg-[#171715] text-white" : "bg-white text-black/45"}`}>{item.label}</a>
              ))}
            </nav>
          </header>

          <div className="p-4 sm:p-6 lg:p-8">
            {subtitle && <p className="mb-6 max-w-2xl text-[10px] leading-6 text-black/42">{subtitle}</p>}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
