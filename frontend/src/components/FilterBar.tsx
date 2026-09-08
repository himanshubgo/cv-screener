import type { Recommendation } from "../types";

export type RecommendationFilter = Recommendation | "all";
export type SortKey = "score_desc" | "score_asc" | "name_asc";

interface FilterBarProps {
  search: string;
  onSearchChange: (v: string) => void;
  recommendationFilter: RecommendationFilter;
  onRecommendationFilterChange: (v: RecommendationFilter) => void;
  humanReviewOnly: boolean;
  onHumanReviewOnlyChange: (v: boolean) => void;
  sortKey: SortKey;
  onSortKeyChange: (v: SortKey) => void;
  visibleCount: number;
  totalCount: number;
}

const RECOMMENDATION_OPTIONS: { value: RecommendationFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "advance", label: "Advance" },
  { value: "hold", label: "Hold" },
  { value: "reject", label: "Reject" },
];

export function FilterBar(props: FilterBarProps) {
  const {
    search,
    onSearchChange,
    recommendationFilter,
    onRecommendationFilterChange,
    humanReviewOnly,
    onHumanReviewOnlyChange,
    sortKey,
    onSortKeyChange,
    visibleCount,
    totalCount,
  } = props;

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <input
        type="search"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search by candidate name…"
        className="min-w-[200px] flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />

      <div className="flex rounded-md border border-slate-300 p-0.5">
        {RECOMMENDATION_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onRecommendationFilterChange(opt.value)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
              recommendationFilter === opt.value ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <label className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
        <input
          type="checkbox"
          checked={humanReviewOnly}
          onChange={(e) => onHumanReviewOnlyChange(e.target.checked)}
          className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
        />
        Needs human review only
      </label>

      <select
        value={sortKey}
        onChange={(e) => onSortKeyChange(e.target.value as SortKey)}
        className="rounded-md border border-slate-300 px-2 py-1.5 text-xs font-medium text-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      >
        <option value="score_desc">Score: high to low</option>
        <option value="score_asc">Score: low to high</option>
        <option value="name_asc">Name: A to Z</option>
      </select>

      <span className="ml-auto text-xs text-slate-400">
        {visibleCount} of {totalCount} shown
      </span>
    </div>
  );
}
