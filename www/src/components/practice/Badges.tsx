import { DIFFICULTY_INFO, type Difficulty } from "@/lib/practice/types";

const TONES: Record<Difficulty, string> = {
  beginner: "bg-slate-100 text-slate-700 ring-slate-600/20 dark:bg-white/5 dark:text-slate-300",
  easy: "bg-emerald-50 text-emerald-800 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300",
  medium: "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300",
  hard: "bg-orange-50 text-orange-800 ring-orange-600/20 dark:bg-orange-500/10 dark:text-orange-300",
  expert: "bg-red-50 text-red-800 ring-red-600/20 dark:bg-red-500/10 dark:text-red-300",
};

export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${TONES[difficulty]}`}>{DIFFICULTY_INFO[difficulty].label}</span>;
}

export function StatusMark({ status }: { status: string | null | undefined }) {
  if (status === "solved") return <span className="text-emerald-700 dark:text-emerald-300" title="Solved independently">✓<span className="sr-only">Solved</span></span>;
  if (status === "solved_assisted") return <span className="text-amber-700 dark:text-amber-300" title="Solved after revealing the solution">◐<span className="sr-only">Solved with solution</span></span>;
  if (status === "attempted") return <span className="text-fg-subtle" title="Attempted">○<span className="sr-only">Attempted</span></span>;
  return <span aria-hidden="true" className="text-transparent">·</span>;
}
