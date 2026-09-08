import type { Recommendation, Verdict } from "../types";

const RECOMMENDATION_STYLES: Record<Recommendation, string> = {
  advance: "bg-emerald-100 text-emerald-800 ring-emerald-600/20",
  hold: "bg-amber-100 text-amber-800 ring-amber-600/20",
  reject: "bg-rose-100 text-rose-800 ring-rose-600/20",
};

export function RecommendationBadge({ value }: { value: Recommendation }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ring-inset ${RECOMMENDATION_STYLES[value]}`}
    >
      {value}
    </span>
  );
}

const VERDICT_STYLES: Record<Verdict, string> = {
  strong: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  adequate: "bg-sky-50 text-sky-700 ring-sky-600/20",
  weak: "bg-amber-50 text-amber-700 ring-amber-600/20",
  missing: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

export function VerdictBadge({ value }: { value: Verdict }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${VERDICT_STYLES[value]}`}
    >
      {value}
    </span>
  );
}

export function ScoreBar({ score, recommendation }: { score: number; recommendation: Recommendation }) {
  const barColor =
    recommendation === "advance" ? "bg-emerald-500" : recommendation === "hold" ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
      </div>
      <span className="w-8 text-right text-sm font-medium tabular-nums text-slate-700">{score}</span>
    </div>
  );
}

export function HumanReviewBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-semibold text-purple-800 ring-1 ring-inset ring-purple-600/20">
      Needs human review
    </span>
  );
}
