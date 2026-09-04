"""Safety controls for cv-screener's agent loop (Step 8).

1. Guardrail - a reject recommendation always routes to a human recruiter for
   review, and every recruiter note is a proposal for a human to approve, never
   text that could go straight to a candidate. `enforce_guardrails()` checks the
   proposed final result against this rule in code - not only in the system
   prompt - and repairs whatever it finds, so a prompt failure can't slip through.
2. Stop rule - the loop ends after it produces one scorecard, or after
   MAX_TOOL_CALLS tool calls, whichever comes first. `check_tool_budget()` is the
   second half; `main.run_loop()` calls it after every tool-executing turn.
"""

from __future__ import annotations

import re
from typing import Any

MAX_TOOL_CALLS = 5

# Phrases that read as a message addressed straight to a candidate - a salutation,
# an outcome notification - rather than an internal note written for a recruiter to
# review. A match means the model drafted outbound-style text instead of a
# recruiter proposal, and the guardrail blocks it.
_CANDIDATE_FACING_RE = re.compile(
    r"\bdear\s+(candidate|applicant|[A-Z][a-z]+)\b"
    r"|\bwe (are pleased|regret) to inform you\b"
    r"|\bcongratulations[,!]?\s+you\b"
    r"|\bunfortunately,?\s+you\b"
    r"|\byou have (been selected|not been selected|been rejected)\b"
    r"|\bthank you for applying\b",
    re.IGNORECASE,
)

SAFE_FALLBACK_NOTE = (
    "[BLOCKED BY GUARDRAIL: the drafted note read as candidate-facing text; a "
    "recruiter must write this note themselves before it is used.]"
)


class ToolBudgetExceeded(RuntimeError):
    """Raised by the loop once MAX_TOOL_CALLS is exceeded with no final answer."""


def check_tool_budget(tool_calls_made: int) -> None:
    """Stop rule, half 2: raise once more than MAX_TOOL_CALLS tool calls were made."""
    if tool_calls_made > MAX_TOOL_CALLS:
        raise ToolBudgetExceeded(
            f"stopped after {tool_calls_made} tool calls (limit {MAX_TOOL_CALLS}) "
            "without a final answer"
        )


def enforce_guardrails(card: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Guardrail, half 1: check the proposed final scorecard, repair, report.

    Returns (repaired card, violations found). `card` is not mutated in place.

    - A reject recommendation must always carry requires_human_review=True. This is
      already guaranteed by main.rate() today (the code computes both), but the
      check is re-verified here, independently, right before the result leaves the
      system - defence in depth against a future refactor of rate() getting it
      wrong, per "check it in code, not only in the prompt."
    - Every recruiter_note is scanned for candidate-facing language. A match is
      blocked and replaced with SAFE_FALLBACK_NOTE; the finding stays marked
      critical, so a human still sees it flagged, just without the unsafe text.
    """
    violations: list[str] = []
    card = dict(card)

    is_reject = card.get("recommendation") == "reject"
    if is_reject and not card.get("requires_human_review"):
        violations.append(
            "recommendation is 'reject' but requires_human_review was not set - forcing it"
        )
    card["requires_human_review"] = is_reject or bool(card.get("requires_human_review"))

    repaired_findings = []
    for finding in card.get("findings", []):
        finding = dict(finding)
        note = finding.get("recruiter_note") or ""
        if note and _CANDIDATE_FACING_RE.search(note):
            violations.append(
                f"recruiter_note for '{finding.get('criterion')}' reads as candidate-facing "
                "text, not an internal recruiter proposal - blocked"
            )
            finding["recruiter_note"] = SAFE_FALLBACK_NOTE
        repaired_findings.append(finding)
    card["findings"] = repaired_findings

    return card, violations
