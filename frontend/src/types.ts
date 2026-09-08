// Mirrors output_contract.py's Scorecard/Finding and api.py's response shapes.
// Keep in sync with the backend by hand - there is no shared schema generator.

export type Verdict = "strong" | "adequate" | "weak" | "missing";
export type Recommendation = "advance" | "hold" | "reject";

export interface Finding {
  criterion: string;
  verdict: Verdict;
  score: number; // 0-100
  evidence: string;
  is_critical: boolean;
  recruiter_note: string;
}

export interface Scorecard {
  candidate_name: string;
  role: string;
  summary: string;
  overall_score: number; // 0-100
  recommendation: Recommendation;
  requires_human_review: boolean;
  findings: Finding[];
  hard_blockers: string[];
  missing_information: string[];
  interview_probes: string[];
  guardrail_violations: string[];
}

export type CandidateStatus = "pending" | "screening" | "ok" | "error";

export interface Candidate {
  id: string;
  filename: string;
  cvText: string;
  status: CandidateStatus;
  card: Scorecard | null;
  error: string | null;
}

export interface CriterionInfo {
  key: string;
  label: string;
  weight: number;
}

export interface HealthInfo {
  ok: boolean;
  has_api_key: boolean;
  criteria: CriterionInfo[];
}
