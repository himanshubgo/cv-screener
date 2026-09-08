import { useEffect } from "react";
import type { Candidate, CriterionInfo } from "../types";
import { HumanReviewBadge, RecommendationBadge, VerdictBadge } from "./Badges";

interface CandidateDetailProps {
  candidate: Candidate | null;
  criteria: CriterionInfo[];
  onClose: () => void;
}

export function CandidateDetail({ candidate, criteria, onClose }: CandidateDetailProps) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!candidate || !candidate.card) return null;
  const card = candidate.card;
  const weightByKey = new Map(criteria.map((c) => [c.key, c.weight]));
  const labelByKey = new Map(criteria.map((c) => [c.key, c.label]));

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-slate-900/30" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-2xl flex-col overflow-y-auto bg-white shadow-xl">
        <div className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">{card.candidate_name}</h2>
            <p className="text-sm text-slate-500">{card.role}</p>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="space-y-6 px-6 py-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-3xl font-bold tabular-nums text-slate-900">{card.overall_score}<span className="text-base font-normal text-slate-400">/100</span></div>
            <RecommendationBadge value={card.recommendation} />
            {card.requires_human_review && <HumanReviewBadge />}
          </div>

          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</h3>
            <p className="mt-1 text-sm text-slate-700">{card.summary}</p>
          </section>

          {card.hard_blockers.length > 0 && (
            <section className="rounded-md border border-rose-200 bg-rose-50 p-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-rose-700">Hard blockers</h3>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-rose-800">
                {card.hard_blockers.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Findings by criterion
            </h3>
            <div className="space-y-3">
              {card.findings.map((f) => (
                <div key={f.criterion} className="rounded-md border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm font-medium text-slate-900">
                      {labelByKey.get(f.criterion) ?? f.criterion}
                      <span className="ml-1.5 text-xs font-normal text-slate-400">
                        weight {weightByKey.get(f.criterion) ?? "?"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <VerdictBadge value={f.verdict} />
                      <span className="text-sm font-semibold tabular-nums text-slate-700">{f.score}/100</span>
                      {f.is_critical && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                          critical
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="mt-2 border-l-2 border-slate-200 pl-2 text-sm italic text-slate-600">
                    “{f.evidence}”
                  </p>
                  {f.is_critical && f.recruiter_note && (
                    <p className="mt-2 rounded bg-amber-50 px-2 py-1.5 text-sm text-amber-900">
                      <span className="font-semibold">Recruiter note (proposal, needs approval): </span>
                      {f.recruiter_note}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>

          {card.missing_information.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Missing information</h3>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-slate-700">
                {card.missing_information.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </section>
          )}

          {card.interview_probes.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Interview probes</h3>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-slate-700">
                {card.interview_probes.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </section>
          )}

          {card.guardrail_violations.length > 0 && (
            <section className="rounded-md border border-purple-200 bg-purple-50 p-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-purple-700">
                Guardrail actions taken
              </h3>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-purple-800">
                {card.guardrail_violations.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          <p className="border-t border-slate-100 pt-3 text-xs text-slate-400">
            This scorecard is a recruiter aid, not a decision — every result, especially a reject, should be
            reviewed by a human before acting on it.
          </p>
        </div>
      </div>
    </div>
  );
}
