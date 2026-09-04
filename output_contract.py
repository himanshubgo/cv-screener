"""Output contract for cv-screener: the typed scorecard shape and its validator.

This module defines the contract only - no model calls, no scoring logic, no CLI.
`Scorecard` is what a completed screening must look like: a 0-100 overall score, an
advance/hold/reject recommendation, one finding per criterion, and a recruiter note
on every finding marked critical. `validate_scorecard()` turns a raw dict (e.g. from
`json.loads()`) into a `Scorecard`, or raises `ScorecardValidationError` listing every
field that is missing, mistyped, or out of range.

Criterion keys and verdict labels are imported from `prompt.py` rather than redefined
here, so the contract can never drift from the criteria the model is actually asked
to score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prompt import CRITERION_KEYS, VERDICTS

RECOMMENDATIONS = ("advance", "hold", "reject")
SCORE_MIN, SCORE_MAX = 0, 100

REQUIRED_TOP_FIELDS = (
    "candidate_name",
    "summary",
    "overall_score",
    "recommendation",
    "requires_human_review",
    "findings",
    "hard_blockers",
    "missing_information",
    "interview_probes",
)
REQUIRED_FINDING_FIELDS = (
    "criterion",
    "verdict",
    "score",
    "evidence",
    "is_critical",
    "recruiter_note",
)


class ScorecardValidationError(ValueError):
    """Raised by validate_scorecard() with every problem found, not just the first."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        message = "invalid scorecard:\n  - " + "\n  - ".join(errors)
        super().__init__(message)


@dataclass(frozen=True)
class Finding:
    """One criterion's result."""

    criterion: str  # one of prompt.CRITERION_KEYS
    verdict: str  # one of prompt.VERDICTS
    score: int  # 0-100
    evidence: str  # quote or close paraphrase from the CV
    is_critical: bool
    recruiter_note: str  # required (non-empty) when is_critical is True


@dataclass(frozen=True)
class Scorecard:
    """The complete, validated screening result for one candidate."""

    candidate_name: str
    summary: str
    overall_score: int  # 0-100
    recommendation: str  # one of RECOMMENDATIONS
    requires_human_review: bool  # the Step 8 guardrail: always true when recommendation == "reject"
    findings: tuple[Finding, ...]  # one per criterion
    hard_blockers: tuple[str, ...]
    missing_information: tuple[str, ...]
    interview_probes: tuple[str, ...]


def validate_scorecard(data: Any) -> Scorecard:
    """Validate a raw dict against the scorecard contract.

    Returns a `Scorecard` on success. Raises `ScorecardValidationError` - carrying
    every problem found, not just the first - if a required field is missing, has the
    wrong type, holds a value outside its allowed range/enum, if `findings` does not
    cover every criterion exactly once, or if a finding marked critical has no
    recruiter note.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        raise ScorecardValidationError(
            [f"top-level result must be an object, got {type(data).__name__}"]
        )

    for name in REQUIRED_TOP_FIELDS:
        if name not in data:
            errors.append(f"missing required field '{name}'")

    _check_nonempty_str(errors, "candidate_name", data.get("candidate_name"), "candidate_name" in data)
    _check_nonempty_str(errors, "summary", data.get("summary"), "summary" in data)

    overall_score = data.get("overall_score")
    if "overall_score" in data:
        _check_score(errors, "overall_score", overall_score)

    recommendation = data.get("recommendation")
    if "recommendation" in data and recommendation not in RECOMMENDATIONS:
        errors.append(f"'recommendation' must be one of {RECOMMENDATIONS}, got {recommendation!r}")

    requires_human_review = data.get("requires_human_review")
    if "requires_human_review" in data:
        if not isinstance(requires_human_review, bool):
            errors.append(
                f"'requires_human_review' must be a boolean, got {type(requires_human_review).__name__}"
            )
        elif recommendation == "reject" and requires_human_review is not True:
            errors.append("'requires_human_review' must be true whenever recommendation is 'reject'")

    findings: list[Finding] = []
    if "findings" in data:
        findings_raw = data["findings"]
        if not isinstance(findings_raw, list) or not findings_raw:
            errors.append("'findings' must be a non-empty list")
        else:
            seen: set[str] = set()
            for i, raw in enumerate(findings_raw):
                finding_errors, finding = _validate_finding(raw, i)
                errors.extend(finding_errors)
                if finding is None:
                    continue
                if finding.criterion in seen:
                    errors.append(f"findings[{i}]: duplicate finding for criterion '{finding.criterion}'")
                else:
                    seen.add(finding.criterion)
                    findings.append(finding)
            missing = [c for c in CRITERION_KEYS if c not in seen]
            if missing:
                errors.append(f"findings missing for criteria: {missing}")

    for name in ("hard_blockers", "missing_information", "interview_probes"):
        if name in data and not _is_str_list(data[name]):
            errors.append(f"'{name}' must be a list of strings")

    if errors:
        raise ScorecardValidationError(errors)

    return Scorecard(
        candidate_name=data["candidate_name"],
        summary=data["summary"],
        overall_score=overall_score,
        recommendation=recommendation,
        requires_human_review=requires_human_review,
        findings=tuple(findings),
        hard_blockers=tuple(data["hard_blockers"]),
        missing_information=tuple(data["missing_information"]),
        interview_probes=tuple(data["interview_probes"]),
    )


def _validate_finding(raw: Any, index: int) -> tuple[list[str], Finding | None]:
    prefix = f"findings[{index}]"
    if not isinstance(raw, dict):
        return [f"{prefix} must be an object, got {type(raw).__name__}"], None

    errors: list[str] = []
    for name in REQUIRED_FINDING_FIELDS:
        if name not in raw:
            errors.append(f"{prefix} missing required field '{name}'")
    if errors:
        return errors, None

    criterion = raw["criterion"]
    if criterion not in CRITERION_KEYS:
        errors.append(f"{prefix}.criterion must be one of {CRITERION_KEYS}, got {criterion!r}")

    verdict = raw["verdict"]
    if verdict not in VERDICTS:
        errors.append(f"{prefix}.verdict must be one of {VERDICTS}, got {verdict!r}")

    _check_score(errors, f"{prefix}.score", raw["score"])

    evidence = raw["evidence"]
    if not isinstance(evidence, str) or not evidence.strip():
        errors.append(f"{prefix}.evidence must be a non-empty string")

    is_critical = raw["is_critical"]
    if not isinstance(is_critical, bool):
        errors.append(f"{prefix}.is_critical must be a boolean, got {type(is_critical).__name__}")

    recruiter_note = raw["recruiter_note"]
    if not isinstance(recruiter_note, str):
        errors.append(f"{prefix}.recruiter_note must be a string, got {type(recruiter_note).__name__}")
    elif is_critical is True and not recruiter_note.strip():
        errors.append(f"{prefix}.recruiter_note is required when is_critical is true")

    if errors:
        return errors, None

    return [], Finding(
        criterion=criterion,
        verdict=verdict,
        score=raw["score"],
        evidence=evidence,
        is_critical=is_critical,
        recruiter_note=recruiter_note,
    )


def _check_nonempty_str(errors: list[str], name: str, value: Any, present: bool) -> None:
    if not present:
        return
    if not isinstance(value, str):
        errors.append(f"'{name}' must be a string, got {type(value).__name__}")
    elif not value.strip():
        errors.append(f"'{name}' must not be empty")


def _check_score(errors: list[str], name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"'{name}' must be an integer, got {type(value).__name__}")
    elif not (SCORE_MIN <= value <= SCORE_MAX):
        errors.append(f"'{name}' must be between {SCORE_MIN} and {SCORE_MAX}, got {value}")


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)
