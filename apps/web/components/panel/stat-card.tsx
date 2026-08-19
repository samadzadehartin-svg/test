export function StatCard({ label, value, hint, tone = "light" }: { label: string; value: string; hint?: string; tone?: "light" | "dark" | "gold" }) {
  const toneClass = tone === "dark" ? "bg-[#171715] text-white" : tone === "gold" ? "bg-[#e9dfcc] text-[#171715]" : "bg-white text-[#171715]";
  return (
    <article className={`rounded-[20px] border border-black/[0.055] p-5 ${toneClass}`}>
      <span className={`text-[8px] font-bold ${tone === "dark" ? "text-white/38" : "text-black/38"}`}>{label}</span>
      <strong className="mt-3 block text-2xl font-bold tracking-[-0.04em] sm:text-3xl">{value}</strong>
      {hint && <span className={`mt-2 block text-[8px] ${tone === "dark" ? "text-white/40" : "text-black/38"}`}>{hint}</span>}
    </article>
  );
}
