import type { Candidate } from "../types";
import { RecommendationBadge, ScoreBar, HumanReviewBadge } from "./Badges";

interface ShortlistTableProps {
  candidates: Candidate[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRetry: (id: string) => void;
}

export function ShortlistTable({ candidates, selectedId, onSelect, onRetry }: ShortlistTableProps) {
  if (candidates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white py-16 text-center">
        <p className="text-sm font-medium text-slate-600">No candidates yet</p>
        <p className="mt-1 text-xs text-slate-400">Import CVs on the left to build the shortlist.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th className="w-10 px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">#</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Candidate</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Score</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Recommendation</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Flags</th>
            <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">File</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {candidates.map((c, i) => (
            <Row key={c.id} rank={i + 1} candidate={c} selected={c.id === selectedId} onSelect={onSelect} onRetry={onRetry} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({
  rank,
  candidate,
  selected,
  onSelect,
  onRetry,
}: {
  rank: number;
  candidate: Candidate;
  selected: boolean;
  onSelect: (id: string) => void;
  onRetry: (id: string) => void;
}) {
  const { id, filename, status, card, error } = candidate;

  if (status === "pending" || status === "screening") {
    return (
      <tr className="bg-white">
        <td className="px-4 py-3 text-sm text-slate-400">{rank}</td>
        <td className="px-4 py-3 text-sm text-slate-500" colSpan={4}>
          <span className="inline-flex items-center gap-2">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
            {status === "screening" ? "Screening…" : "Queued…"}
          </span>
        </td>
        <td className="px-4 py-3 text-xs text-slate-400">{filename}</td>
      </tr>
    );
  }

  if (status === "error") {
    return (
      <tr className="bg-rose-50/40">
        <td className="px-4 py-3 text-sm text-slate-400">{rank}</td>
        <td className="px-4 py-3 text-sm text-rose-700" colSpan={4}>
          <span className="font-medium">Failed:</span> {error}
          <button
            onClick={() => onRetry(id)}
            className="ml-3 rounded border border-rose-300 px-2 py-0.5 text-xs font-medium text-rose-700 hover:bg-rose-100"
          >
            Retry
          </button>
        </td>
        <td className="px-4 py-3 text-xs text-slate-400">{filename}</td>
      </tr>
    );
  }

  if (!card) return null;
  const criticalCount = card.findings.filter((f) => f.is_critical).length;

  return (
    <tr
      onClick={() => onSelect(id)}
      className={`cursor-pointer transition-colors ${selected ? "bg-indigo-50" : "bg-white hover:bg-slate-50"}`}
    >
      <td className="px-4 py-3 text-sm text-slate-400">{rank}</td>
      <td className="px-4 py-3">
        <div className="text-sm font-medium text-slate-900">{card.candidate_name}</div>
        <div className="line-clamp-1 max-w-xs text-xs text-slate-500">{card.summary}</div>
      </td>
      <td className="px-4 py-3">
        <ScoreBar score={card.overall_score} recommendation={card.recommendation} />
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col items-start gap-1">
          <RecommendationBadge value={card.recommendation} />
          {card.requires_human_review && <HumanReviewBadge />}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-slate-600">
        {criticalCount > 0 ? (
          <span className="font-medium text-amber-700">{criticalCount} critical</span>
        ) : (
          <span className="text-slate-400">—</span>
        )}
        {card.hard_blockers.length > 0 && (
          <div className="text-xs font-medium text-rose-600">{card.hard_blockers.length} hard blocker(s)</div>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-slate-400">{filename}</td>
    </tr>
  );
}
