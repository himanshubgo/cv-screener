"""HTTP API for cv-screener - the frontend's only entry point into the agent.

Wraps the existing pipeline (`main.screen` -> `main.rate` ->
`guardrails.enforce_guardrails` -> `output_contract.validate_scorecard`) exactly as
`main.py`'s CLI does, so the API and the CLI can never disagree about what a
screening run produces. No screening logic lives here - this module only accepts
CVs over HTTP, runs the existing pipeline per CV (concurrently, with a cap), and
serializes the result.

    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any

import anthropic
from fastapi import FastAPI, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from guardrails import ToolBudgetExceeded, enforce_guardrails
from main import load_env, rate, screen
from output_contract import ScorecardValidationError, validate_scorecard
from prompt import CRITERIA

# How many CVs to screen at once. Each screening call is a real model request, so
# this is a courtesy cap against provider rate limits, not a hard system limit.
MAX_CONCURRENT_SCREENINGS = 3

load_env()
app = FastAPI(title="cv-screener API")

# The frontend is a separate dev server (Vite, default http://localhost:5173) in
# development; loosened to any origin here since this API carries no auth/cookies
# and is meant to run on a recruiter's own machine, not as a public service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_client: anthropic.Anthropic | None = None
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCREENINGS)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


class CriterionOut(BaseModel):
    key: str
    label: str
    weight: int


class HealthOut(BaseModel):
    ok: bool
    has_api_key: bool
    criteria: list[CriterionOut]


@app.get("/api/health", response_model=HealthOut)
def health() -> HealthOut:
    has_key = bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )
    return HealthOut(
        ok=True,
        has_api_key=has_key,
        criteria=[CriterionOut(key=c["key"], label=c["label"], weight=c["weight"]) for c in CRITERIA],
    )


def _screen_one_sync(cv_text: str) -> dict[str, Any]:
    """The same pipeline as `main.main()`, minus argument parsing and printing."""
    client = _get_client()
    raw = screen(cv_text, client)
    card = rate(raw)
    card, violations = enforce_guardrails(card)
    validated = validate_scorecard(card)  # raises ScorecardValidationError on failure
    result = asdict(validated) if is_dataclass(validated) else dict(validated)
    result["role"] = card.get("role")
    result["guardrail_violations"] = violations
    return result


async def _screen_one(candidate_id: str, filename: str, cv_text: str) -> dict[str, Any]:
    async with _semaphore:
        try:
            if not cv_text.strip():
                raise ValueError("the CV is empty")
            card = await run_in_threadpool(_screen_one_sync, cv_text)
            return {"id": candidate_id, "filename": filename, "status": "ok", "card": card}
        except ToolBudgetExceeded as e:
            return {"id": candidate_id, "filename": filename, "status": "error", "error": str(e)}
        except ScorecardValidationError as e:
            return {
                "id": candidate_id,
                "filename": filename,
                "status": "error",
                "error": "invalid scorecard: " + "; ".join(e.errors),
            }
        except Exception as e:  # noqa: BLE001 - one candidate's failure must not sink the batch
            return {"id": candidate_id, "filename": filename, "status": "error", "error": str(e)}


@app.post("/api/screen-batch")
async def screen_batch(files: list[UploadFile]) -> dict[str, Any]:
    """Screen every uploaded CV (plain-text files) and return one result per file.

    Runs up to `MAX_CONCURRENT_SCREENINGS` screenings in parallel. A single
    candidate's failure (bad file, model error, invalid scorecard) is reported as
    that candidate's result and does not affect the others.
    """
    jobs = []
    for f in files:
        raw = await f.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        jobs.append(_screen_one(str(uuid.uuid4()), f.filename or "cv.txt", text))

    results = await asyncio.gather(*jobs)
    return {"results": results}


@app.post("/api/screen-text")
async def screen_text(payload: dict[str, str]) -> dict[str, Any]:
    """Screen one CV given as raw text (e.g. pasted in the UI) rather than a file."""
    cv_text = payload.get("cv_text", "")
    filename = payload.get("filename", "pasted-cv.txt")
    result = await _screen_one(str(uuid.uuid4()), filename, cv_text)
    return result
