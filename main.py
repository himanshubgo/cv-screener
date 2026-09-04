"""cv-screener - entry point.

Reads one raw CV as plain text and prints a screening scorecard for the BGO call
centre agent role: a 0-100 score, an advance/hold/reject recommendation, a finding
per criterion and a recruiter note per critical finding.

    python main.py sample_cv.txt
    python main.py sample_cv.txt --verbose    # show every loop turn as it happens
    Get-Content sample_cv.txt | python main.py -      # or --json for raw JSON
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic

from prompt import CRITERIA, ROLE, SCORECARD_SCHEMA, SYSTEM_PROMPT, build_user_message
from tools import TOOLS, run_tool
from guardrails import MAX_TOOL_CALLS, ToolBudgetExceeded, check_tool_budget, enforce_guardrails
from output_contract import ScorecardValidationError, validate_scorecard

MODEL = "claude-opus-5"
MAX_TOKENS = 16000
EFFORT = "high"  # low | medium | high | xhigh | max

SMOKE_TEST_PROMPT = "Say hello and name the model you are."

ADVANCE_AT = 75  # weighted score at or above this -> advance
HOLD_AT = 55  # ... and at or above this -> hold, below -> reject

WEIGHTS = {c["key"]: c["weight"] for c in CRITERIA}
LABELS = {c["key"]: c["label"] for c in CRITERIA}


def load_env(path: Path | None = None) -> None:
    """Minimal .env reader so the project needs no dotenv dependency.

    Real environment variables win; the file only fills in what is unset.
    """
    path = path or Path(__file__).with_name(".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def smoke_test(client: anthropic.Anthropic) -> str:
    """Bare single message to MODEL - no system prompt, no tools, no loop.

    Just enough to confirm the API key, the SDK and MODEL all work end to end.
    Prints the reply and returns it.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": SMOKE_TEST_PROMPT}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    print(text)
    return text


def _log_turn(turn: int, response: Any) -> None:
    """Print what happened this turn: the model's visible output and any tool call."""
    print(f"--- turn {turn} (stop_reason={response.stop_reason}) ---")
    for block in response.content:
        if block.type == "text" and block.text:
            print(f"  model: {block.text}")
        elif block.type == "thinking" and getattr(block, "thinking", ""):
            print(f"  thinking: {block.thinking}")
        elif block.type == "tool_use":
            print(f"  tool call -> {block.name}({json.dumps(block.input)})")


def run_loop(
    messages: list[dict[str, Any]],
    client: anthropic.Anthropic,
    *,
    schema: dict[str, Any] | None = None,
    verbose: bool = False,
) -> str:
    """The agent loop (Step 7), with the Step 8 stop rule wired in.

    Calls MODEL with the system prompt, `messages` and whatever tools are in
    TOOLS. A `tool_use` response is executed - via `run_tool()` - and its result is
    fed back as the next turn; a normal (or schema-constrained) message is the final
    answer and is returned as text. Ends the loop the moment a final answer arrives,
    or raises `ToolBudgetExceeded` the moment more than `MAX_TOOL_CALLS` tool calls
    have been made without one.

    Pass `verbose=True` to print every turn - model output, tool calls, tool
    results - as it happens.
    """
    tool_calls_made = 0
    turn = 0

    while True:
        turn += 1
        request: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            # Stable prefix, cached so repeat calls only pay for what varies below.
            "system": [
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": messages,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT},
            # If a safety classifier declines the request, retry it server-side on
            # Anthropic's recommended fallback model inside the same call.
            "betas": ["server-side-fallback-2026-07-01"],
            "fallbacks": "default",
        }
        if TOOLS:
            request["tools"] = TOOLS
        if schema is not None:
            request["output_config"]["format"] = {"type": "json_schema", "schema": schema}

        response = client.beta.messages.create(**request)

        if verbose:
            _log_turn(turn, response)

        if response.stop_reason == "refusal":
            detail = getattr(response.stop_details, "explanation", None)
            raise RuntimeError(f"Model declined: {detail}")

        if response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            tool_calls_made += len(tool_use_blocks)

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in tool_use_blocks:
                result = run_tool(block.name, block.input)
                if verbose:
                    print(f"  tool result <- {block.name}: {result}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
            messages.append({"role": "user", "content": tool_results})

            check_tool_budget(tool_calls_made)  # raises ToolBudgetExceeded past the cap
            continue

        # A normal (non-tool-use) message: the final answer. Return it and stop.
        return next((b.text for b in response.content if b.type == "text"), "")


def screen(cv_text: str, client: anthropic.Anthropic, *, verbose: bool = False) -> dict[str, Any]:
    """One screening pass: raw CV text in, validated scorecard fields out."""
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": build_user_message(cv_text)}
    ]
    text = run_loop(messages, client, schema=SCORECARD_SCHEMA, verbose=verbose)
    return json.loads(text)


def rate(scorecard: dict[str, Any]) -> dict[str, Any]:
    """Add the composite score, the recommendation, and the human-review flag.

    Deliberately computed here rather than asked of the model: weights, thresholds,
    and the reject -> human-review routing are policy, and policy should be
    reproducible and auditable, not something a model call could forget to set.
    `enforce_guardrails()` re-checks the human-review flag independently anyway
    (Step 8) - this is the first, not the only, place it is set correctly.
    """
    findings = [f for f in scorecard["findings"] if f["criterion"] in WEIGHTS]
    weighted = sum(
        max(0, min(100, f["score"])) * WEIGHTS[f["criterion"]] for f in findings
    )
    total_weight = sum(WEIGHTS[f["criterion"]] for f in findings)
    overall = round(weighted / total_weight) if total_weight else 0

    blockers = scorecard.get("hard_blockers") or []
    if blockers:
        recommendation = "reject"
    elif overall >= ADVANCE_AT:
        recommendation = "advance"
    elif overall >= HOLD_AT:
        recommendation = "hold"
    else:
        recommendation = "reject"

    return {
        **scorecard,
        "role": ROLE,
        "overall_score": overall,
        "recommendation": recommendation,
        "requires_human_review": recommendation == "reject",
    }


def render(card: dict[str, Any]) -> str:
    """Recruiter-readable version of the same scorecard."""
    review_flag = "  [REQUIRES HUMAN REVIEW]" if card.get("requires_human_review") else ""
    lines = [
        f"{card['candidate_name']} - {card['role']}",
        f"Score {card['overall_score']}/100 - {card['recommendation'].upper()}{review_flag}",
        "",
        card["summary"],
        "",
        "Findings",
    ]
    for finding in card["findings"]:
        key = finding["criterion"]
        flag = " [CRITICAL]" if finding["is_critical"] else ""
        lines.append(
            f"  {LABELS.get(key, key)} (w{WEIGHTS.get(key, 0)}): "
            f"{finding['score']}/100 {finding['verdict']}{flag}"
        )
        lines.append(f"      {finding['evidence']}")
        if finding["is_critical"] and finding["recruiter_note"]:
            lines.append(f"      note: {finding['recruiter_note']}")

    for title, key in (
        ("Hard blockers", "hard_blockers"),
        ("Missing information", "missing_information"),
        ("Interview probes", "interview_probes"),
    ):
        items = card.get(key) or []
        if items:
            lines += ["", title] + [f"  - {item}" for item in items]

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Screen a CV for the {ROLE} role.")
    parser.add_argument("cv", nargs="?", help="path to a plain-text CV, or - to read stdin")
    parser.add_argument(
        "--json", action="store_true", help="print the raw scorecard JSON"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="print every loop turn - model output, tool calls, tool results",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="send a hard-coded throwaway prompt to MODEL and print the reply, "
        "to confirm the API key/SDK/model id work - skips screening",
    )
    args = parser.parse_args(argv)

    load_env()
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("Set ANTHROPIC_API_KEY in .env (copy .env.example).", file=sys.stderr)
        return 2

    if args.smoke_test:
        smoke_test(anthropic.Anthropic())
        return 0

    if not args.cv:
        parser.error("cv is required unless --smoke-test is given")

    cv_text = sys.stdin.read() if args.cv == "-" else Path(args.cv).read_text("utf-8")
    if not cv_text.strip():
        parser.error("the CV is empty")

    client = anthropic.Anthropic()
    try:
        raw = screen(cv_text, client, verbose=args.verbose)
    except ToolBudgetExceeded as e:
        # Stop rule tripped (Step 8): report plainly instead of crashing.
        print(f"Could not complete within the limit: {e}", file=sys.stderr)
        return 3

    card = rate(raw)
    card, violations = enforce_guardrails(card)  # guardrail (Step 8)
    for v in violations:
        print(f"GUARDRAIL: {v}", file=sys.stderr)

    try:
        validate_scorecard(card)  # Step 2's validator, reused as the final gate
    except ScorecardValidationError as e:
        print(f"Invalid scorecard: {e.errors}", file=sys.stderr)
        return 4

    print(json.dumps(card, indent=2) if args.json else render(card))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
