import { useEffect, useMemo, useState } from "react";
import { fetchHealth, readFileAsText, screenText } from "./api";
import { runPool } from "./lib/pool";
import type { Candidate, CriterionInfo, HealthInfo } from "./types";
import { Header } from "./components/Header";
import { UploadPanel } from "./components/UploadPanel";
import { FilterBar, type RecommendationFilter, type SortKey } from "./components/FilterBar";
import { ShortlistTable } from "./components/ShortlistTable";
import { CandidateDetail } from "./components/CandidateDetail";

const STORAGE_KEY = "cv-screener:candidates";
const MAX_CONCURRENT = 3;

function loadStoredCandidates(): Candidate[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Candidate[];
    // A page reload mid-screening leaves no promise to resume - surface those as errors.
    return parsed.map((c) =>
      c.status === "pending" || c.status === "screening"
        ? { ...c, status: "error", error: "interrupted by page reload" }
        : c,
    );
  } catch {
    return [];
  }
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}

export default function App() {
  const [candidates, setCandidates] = useState<Candidate[]>(loadStoredCandidates);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isScreening, setIsScreening] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [recommendationFilter, setRecommendationFilter] = useState<RecommendationFilter>("all");
  const [humanReviewOnly, setHumanReviewOnly] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("score_desc");

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((e) => setHealthError(e instanceof Error ? e.message : "could not reach backend"));
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(candidates));
    } catch {
      // sessionStorage can throw in private-browsing/quota-exceeded cases - losing
      // the persisted copy is not fatal, the in-memory shortlist still works.
    }
  }, [candidates]);

  function updateCandidate(id: string, patch: Partial<Candidate>) {
    setCandidates((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  }

  async function screenOne(entry: Candidate) {
    updateCandidate(entry.id, { status: "screening" });
    const res = await screenText(entry.filename, entry.cvText);
    if (res.status === "ok" && res.card) {
      updateCandidate(entry.id, { status: "ok", card: res.card, error: null });
    } else {
      updateCandidate(entry.id, { status: "error", error: res.error ?? "unknown error" });
    }
    setProgress((p) => (p ? { done: p.done + 1, total: p.total } : p));
  }

  async function handleScreen(files: File[]) {
    const entries: Candidate[] = await Promise.all(
      files.map(async (f) => ({
        id: newId(),
        filename: f.name,
        cvText: await readFileAsText(f).catch(() => ""),
        status: "pending" as const,
        card: null,
        error: null,
      })),
    );

    setCandidates((prev) => [...prev, ...entries]);
    setIsScreening(true);
    setProgress({ done: 0, total: entries.length });

    await runPool(entries, MAX_CONCURRENT, screenOne);

    setIsScreening(false);
    setProgress(null);
  }

  async function handleRetry(id: string) {
    const target = candidates.find((c) => c.id === id);
    if (!target) return;
    await screenOne(target);
  }

  function handleClear() {
    setCandidates([]);
    setSelectedId(null);
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return candidates.filter((c) => {
      if (c.status !== "ok" || !c.card) return true;
      if (q && !c.card.candidate_name.toLowerCase().includes(q)) return false;
      if (recommendationFilter !== "all" && c.card.recommendation !== recommendationFilter) return false;
      if (humanReviewOnly && !c.card.requires_human_review) return false;
      return true;
    });
  }, [candidates, search, recommendationFilter, humanReviewOnly]);

  const sorted = useMemo(() => {
    const ok = filtered.filter((c) => c.status === "ok" && c.card);
    const rest = filtered.filter((c) => !(c.status === "ok" && c.card));
    ok.sort((a, b) => {
      const ca = a.card!;
      const cb = b.card!;
      if (sortKey === "score_desc") return cb.overall_score - ca.overall_score;
      if (sortKey === "score_asc") return ca.overall_score - cb.overall_score;
      return ca.candidate_name.localeCompare(cb.candidate_name);
    });
    return [...ok, ...rest];
  }, [filtered, sortKey]);

  const selected = candidates.find((c) => c.id === selectedId) ?? null;
  const criteria: CriterionInfo[] = health?.criteria ?? [];

  return (
    <div className="min-h-screen">
      <Header health={health} healthError={healthError} />

      <main className="mx-auto max-w-7xl px-6 py-6">
        {healthError && (
          <div className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800 ring-1 ring-inset ring-rose-600/20">
            Can't reach the backend at /api ({healthError}). Start it with{" "}
            <code className="rounded bg-rose-100 px-1 py-0.5">uvicorn api:app --reload --port 8000</code>.
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
          <div className="lg:sticky lg:top-6 lg:self-start">
            <UploadPanel
              onScreen={handleScreen}
              isScreening={isScreening}
              progress={progress}
              candidateCount={candidates.length}
              onClear={handleClear}
            />
          </div>

          <div className="space-y-4">
            <FilterBar
              search={search}
              onSearchChange={setSearch}
              recommendationFilter={recommendationFilter}
              onRecommendationFilterChange={setRecommendationFilter}
              humanReviewOnly={humanReviewOnly}
              onHumanReviewOnlyChange={setHumanReviewOnly}
              sortKey={sortKey}
              onSortKeyChange={setSortKey}
              visibleCount={sorted.length}
              totalCount={candidates.length}
            />
            <ShortlistTable candidates={sorted} selectedId={selectedId} onSelect={setSelectedId} onRetry={handleRetry} />
          </div>
        </div>
      </main>

      <CandidateDetail candidate={selected} criteria={criteria} onClose={() => setSelectedId(null)} />
    </div>
  );
}
