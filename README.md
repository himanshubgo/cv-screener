# cv-screener

One job: screen a candidate CV for fitness as a **BGO call centre agent** and produce a
hiring recommendation. Input is a raw CV as plain text; output is a screening scorecard
— score 0–100, `advance` / `hold` / `reject`, a finding per criterion, and a recruiter
note per critical finding.

## File layout

- [main.py](main.py) — entry point: reads the CV, makes the one Claude Opus 5 call, computes the weighted score and the recommendation, prints the scorecard.
- [prompt.py](prompt.py) — everything the agent is told: the system prompt, the seven weighted criteria, and the JSON schema the scorecard must match.
- [tools.py](tools.py) — the tool surface, empty for now: register a definition plus a handler and `main.py` starts running the tool loop unchanged.
- [api.py](api.py) — HTTP wrapper around the same pipeline (`screen` → `rate` → `enforce_guardrails` → `validate_scorecard`), for the frontend in [frontend/](frontend/).
- [frontend/](frontend/) — React + Tailwind recruiter UI: import a batch of CVs, screen them against `api.py`, browse the results as a ranked/filterable shortlist with full per-candidate detail. Two ways to run it:
  - [frontend/](frontend/) itself — a Vite/TypeScript project, needs Node.js + `npm install`.
  - [frontend/no-build/index.html](frontend/no-build/index.html) — the same app with no build step: React, Babel (in-browser JSX) and Tailwind load from a CDN via `<script>` tags, so it runs from **just Python's built-in web server** — no Node/npm, no admin rights, no install of any kind. Use this if Node.js isn't available (e.g. blocked by an org policy).

Plus `.env` for `ANTHROPIC_API_KEY` (copy `.env.example`), `requirements.txt`
(`anthropic`, plus `fastapi`/`uvicorn`/`python-multipart` for `api.py`), and
`sample_cv.txt` to try it on.

## Run — CLI

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# put your key in .env
python main.py sample_cv.txt
python main.py sample_cv.txt --json
Get-Content sample_cv.txt | python main.py -
```

## Run — web app, no Node.js required (recommended if Node isn't available)

Two processes, both plain Python - no install beyond `requirements.txt`:

```powershell
# Terminal 1 - API (same venv/.env as the CLI above)
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Terminal 2 - static file server for the frontend
cd frontend\no-build
python -m http.server 5500
```

Open **http://127.0.0.1:5500** in a browser. That page talks to the API at
`http://127.0.0.1:8000` directly (cross-origin `fetch`, allowed by `api.py`'s CORS
setting) - if you run the API on a different port, edit `API_BASE` near the top of
[frontend/no-build/index.html](frontend/no-build/index.html)'s script to match.

React, Babel (which transforms the JSX in the browser) and Tailwind are loaded from
a CDN via `<script>` tags in that one HTML file - nothing is installed or compiled,
so this needs no admin rights and no package manager, only outbound access to
`unpkg.com` and `cdn.tailwindcss.com`.

## Run — web app via Vite (if Node.js is available)

Same two-process shape, but the frontend runs through Vite's dev server instead of
a static file server - use this once Node.js/npm are available; it gives hot
reload and a production build (`npm run build`), which the no-build page doesn't.

```powershell
# Terminal 1 - API (same venv/.env as the CLI above)
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Terminal 2 - frontend
cd frontend
npm install
npm run dev
```

Open the frontend dev server URL (default `http://localhost:5173`); it proxies
`/api/*` to `http://127.0.0.1:8000`.

## Using either version of the app

Drop one or more plain-text CVs (`.txt`) onto
the import panel — each is sent to `/api/screen-text` and screened independently
(up to 3 at a time), so results populate the shortlist as they finish rather than
all at once. The table is sortable by score/name, filterable by recommendation and
by "needs human review", and searchable by candidate name; click a row for the full
scorecard — findings per criterion with evidence and recruiter notes, hard
blockers, missing information, and interview probes.

`api.py` never lets one candidate's failure sink a batch: a bad file, a model
error, or a scorecard that fails validation comes back as that candidate's
`status: "error"` with a message, and the row gets a Retry button, instead of
failing the whole import.

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
