# cv-screener

One job: screen a candidate CV for fitness as a **BGO call centre agent** and produce a
hiring recommendation. Input is a raw CV as plain text; output is a screening scorecard
— score 0–100, `advance` / `hold` / `reject`, a finding per criterion, and a recruiter
note per critical finding.

## File layout

- [main.py](main.py) — entry point: reads the CV, makes the one Claude Opus 5 call, computes the weighted score and the recommendation, prints the scorecard.
- [prompt.py](prompt.py) — everything the agent is told: the system prompt, the seven weighted criteria, and the JSON schema the scorecard must match.
- [tools.py](tools.py) — the tool surface, empty for now: register a definition plus a handler and `main.py` starts running the tool loop unchanged.

Plus `.env` for `ANTHROPIC_API_KEY` (copy `.env.example`), `requirements.txt`
(`anthropic` only), and `sample_cv.txt` to try it on.

## Run

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# put your key in .env
python main.py sample_cv.txt
python main.py sample_cv.txt --json
Get-Content sample_cv.txt | python main.py -
```

## How the recommendation is reached

The model scores each criterion 0–100 with evidence quoted from the CV. `main.py` — not
the model — applies the weights in `CRITERIA` and the thresholds `ADVANCE_AT` / `HOLD_AT`,
so the same CV always yields the same number and the policy is auditable in one place.
Anything the model lists under `hard_blockers` forces `reject`.

The model is instructed to score only job-related evidence, to treat a silent CV as
missing information rather than a negative, and to quote the CV for every finding. The
output is a recruiter aid, not a decision: a human reviews every scorecard.

## Assumption to replace

The role brief in `prompt.py` describes BGO as a high-volume, rotational-shift contact
centre programme, because the account's real requirements weren't specified. Replace
that paragraph and the `CRITERIA` weights with the actual account brief — language bar,
shift pattern, minimum education — before using this on real candidates.
