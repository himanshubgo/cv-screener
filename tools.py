"""Tool surface for cv-screener.

`check_qualifications` (Step 6) runs deterministic checks - experience, skills, red
flags - against CV text using fixed rules (regex/keyword matching), not model
judgment, so results are reproducible and the whole thing runs offline with no
external service. Add more tools the same way: a definition in TOOLS plus a handler
in HANDLERS, and main.py's loop picks it up unchanged.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Callable

# Anthropic tool definitions, sent verbatim to the API.
TOOLS: list[dict[str, Any]] = []

# name -> handler. A handler takes the parsed tool input and returns the text that
# goes back to the model as the tool result.
HANDLERS: dict[str, Callable[[dict[str, Any]], str]] = {}


def run_tool(name: str, payload: dict[str, Any]) -> str:
    """Dispatch one tool call. Errors come back as text so the model can recover."""
    handler = HANDLERS.get(name)
    if handler is None:
        return f"Error: no handler registered for tool {name!r}."
    try:
        return handler(payload)
    except Exception as exc:  # surfaced to the model, not swallowed
        return f"Error running {name}: {exc}"


# --------------------------------------------------------------------------------
# check_qualifications
# --------------------------------------------------------------------------------

MIN_EXPERIENCE_MONTHS = 6

_MONTHS = {
    name: i
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
            ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
            ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december"),
        ],
        start=1,
    )
    for name in names
}

# "Mar 2023 - present", "June 2021 - March 2023", "Jan 2020 to Dec 2020", etc.
_DATE_RANGE_RE = re.compile(
    r"(?P<start_mon>[A-Za-z]{3,9})\.?\s+(?P<start_year>\d{4})\s*(?:-|–|—|to)\s*"
    r"(?P<end>present|current|now|(?P<end_mon>[A-Za-z]{3,9})\.?\s+(?P<end_year>\d{4}))",
    re.IGNORECASE,
)

CONTACT_CENTRE_KEYWORDS = (
    "support", "call cent", "contact cent", "bpo", "customer service",
    "helpdesk", "help desk", "voice support", "chat support", "csr",
)

# Any one of these being present is treated as relevant systems/tooling literacy -
# accounts vary in exactly which stack they run, so this is an "any match", not an
# "all required" list.
KNOWN_SKILLS = (
    "zendesk", "salesforce", "genesys", "avaya", "freshdesk", "five9",
    "crm", "dialer", "dialler", "ticketing", "excel",
)

RED_FLAG_PHRASES = (
    "terminated for cause", "immediate joiner only", "will not work nights",
    "will not work weekends", "no night shifts", "no weekend availability",
    "absconded", "notice period 6 months", "notice period six months",
    "criminal record", "pending litigation against employer",
)


def _month_index(mon_name: str) -> int | None:
    return _MONTHS.get(mon_name[:3].lower() if len(mon_name) >= 3 else mon_name.lower())


def _check_experience(cv_text: str) -> dict[str, Any]:
    today = date.today()
    total_months = 0
    contact_centre_months = 0

    for m in _DATE_RANGE_RE.finditer(cv_text):
        start_mon = _month_index(m.group("start_mon"))
        if start_mon is None:
            continue
        start_year = int(m.group("start_year"))

        if m.group("end").lower() in ("present", "current", "now"):
            end_mon, end_year = today.month, today.year
        else:
            end_mon = _month_index(m.group("end_mon") or "")
            end_year_raw = m.group("end_year")
            if end_mon is None or end_year_raw is None:
                continue
            end_year = int(end_year_raw)

        months = max(0, (end_year * 12 + end_mon) - (start_year * 12 + start_mon))
        total_months += months

        window = cv_text[max(0, m.start() - 80): m.end() + 80].lower()
        if any(kw in window for kw in CONTACT_CENTRE_KEYWORDS):
            contact_centre_months += months

    return {
        "total_months": total_months,
        "contact_centre_months": contact_centre_months,
        "meets_minimum": total_months >= MIN_EXPERIENCE_MONTHS,
        "minimum_required_months": MIN_EXPERIENCE_MONTHS,
    }


def _check_skills(cv_text: str) -> dict[str, Any]:
    lowered = cv_text.lower()
    matched = sorted({kw for kw in KNOWN_SKILLS if kw in lowered})
    return {"matched": matched, "meets_minimum": len(matched) > 0}


def _check_red_flags(cv_text: str) -> dict[str, Any]:
    lowered = cv_text.lower()
    matched = sorted({phrase for phrase in RED_FLAG_PHRASES if phrase in lowered})
    return {"matched_phrases": matched, "clear": len(matched) == 0}


_CHECKS: dict[str, Callable[[str], dict[str, Any]]] = {
    "experience": _check_experience,
    "skills": _check_skills,
    "red_flags": _check_red_flags,
}


def _check_qualifications(payload: dict[str, Any]) -> str:
    cv_text = payload.get("cv_text")
    if not isinstance(cv_text, str) or not cv_text.strip():
        return json.dumps({"error": "cv_text is required and must be non-empty"})

    requested = payload.get("checks") or list(_CHECKS)
    unknown = [c for c in requested if c not in _CHECKS]
    if unknown:
        return json.dumps({"error": f"unknown check(s): {unknown}"})

    return json.dumps({name: _CHECKS[name](cv_text) for name in requested})


TOOLS.append(
    {
        "name": "check_qualifications",
        "description": (
            "Run deterministic checks - total and contact-centre experience in "
            "months, known contact-centre skills/tools mentioned, and known "
            "red-flag phrases - against the candidate's CV text. Call this once "
            "before finalizing any finding that depends on a hard threshold or a "
            "known phrase rather than your own reading of the CV."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "cv_text": {
                    "type": "string",
                    "description": "The full raw CV text to check.",
                },
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["experience", "skills", "red_flags"],
                    },
                    "description": "Which check categories to run. Omit to run all three.",
                },
            },
            "required": ["cv_text"],
            "additionalProperties": False,
        },
    }
)
HANDLERS["check_qualifications"] = _check_qualifications
