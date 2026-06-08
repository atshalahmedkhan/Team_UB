type BadgeProps = {
  children: React.ReactNode;
  tone?: "ok" | "warn" | "neutral" | "running";
};

const tones = {
  ok: "bg-emerald-950 text-emerald-300 border-emerald-800",
  warn: "bg-amber-950 text-amber-300 border-amber-800",
  neutral: "bg-zinc-800 text-zinc-300 border-zinc-700",
  running: "bg-sky-950 text-sky-300 border-sky-800",
};

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
