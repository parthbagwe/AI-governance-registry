# Frontend — AI Model Governance Registry

Next.js 15 (App Router) + TypeScript + Tailwind. Replaces the original
Streamlit dashboard with a deployable web frontend, and talks to the same
FastAPI backend over HTTP.

## Why this exists

Streamlit can't deploy to Vercel — it needs a persistent Python process, and
Vercel runs static output plus serverless functions. Splitting the two means
the frontend can live on Vercel and the API on a platform built for
long-running Python (Render, Railway, Fly).

## Design principle

**This frontend holds no governance logic.** It never decides whether a
transition is legal or whether a score clears the bar. It asks the API and
renders the answer — including rendering the API's rejection message verbatim
when an action is blocked. The rules live in exactly one place,
`app/workflow.py`, so the web UI, the Streamlit dashboard, the drift monitor,
and any future CLI all inherit identical guarantees.

`lib/types.ts` does keep a mirrored copy of the thresholds and the transition
map — but only to warn a user *before* they click. The backend's answer is
always authoritative.

## Run it locally

You need the FastAPI backend running first, in a separate terminal from the
project root:

```powershell
python -m uvicorn app.main:app --reload
```

Then, in a new terminal:

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` in `.env.local`, then open
http://localhost:3000. Unauthenticated visitors are redirected to `/login`.
Supabase email signup is available at `/signup`. In Supabase Authentication →
URL Configuration, add `http://localhost:3000/auth/callback` as an allowed
redirect URL so email confirmations can establish a session.

## Deploying to Vercel

1. Push this repo to GitHub.
2. In Vercel, import the repo and set **Root Directory** to `frontend`.
3. Add `NEXT_PUBLIC_API_URL` (your deployed API's base URL ending in
   `/api/v1`), `NEXT_PUBLIC_SUPABASE_URL`, and
   `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
4. Deploy.

The backend must be reachable over HTTPS and must allow your Vercel origin in
its CORS config. `app/main.py` currently allows `*`, which is fine for a demo —
tighten it to the actual Vercel domain before showing this as production-ready.

## Structure

```
frontend/
├── app/
│   ├── layout.tsx            shell, header, global styles
│   ├── page.tsx              portfolio overview: stats, filters, model table
│   ├── signup/page.tsx       Supabase email/password self-registration
│   ├── models/[id]/page.tsx  model detail, composes the panels below
│   └── not-found.tsx
├── components/
│   ├── Badges.tsx            stage and risk-tier chips
│   ├── PortfolioStats.tsx    the four headline numbers
│   ├── Scorecard.tsx         five-dimension scorecard + pass/fail against tier
│   ├── MetricChart.tsx       time-series of logged metrics (recharts)
│   ├── TrajectoryForecast.tsx projected metrics + regulatory source watchlist
│   ├── AuditTrail.tsx        append-only stage history, emergency events marked
│   ├── LineagePanel.tsx      source tables and features
│   ├── ActionPanel.tsx       stage transitions + emergency kill switch
│   ├── ExplainPanel.tsx      SHAP explanation for the SME credit scorer
│   └── States.tsx            loading / error / empty
└── lib/
    ├── api.ts                fetch wrapper, ApiError carries the API's message
    ├── types.ts              mirrors app/schemas.py
    └── display.ts            technical value -> plain English, display only
```

## API surface consumed

| Method | Path | Used by |
|---|---|---|
| GET | `/models` | portfolio page |
| GET | `/models/{id}` | detail page |
| GET | `/models/{id}/metrics` | metric chart |
| GET | `/models/{id}/forecast` | trajectory forecast and regulatory outlook |
| GET | `/models/{id}/history` | audit trail |
| GET | `/models/{id}/lineage` | lineage panel |
| POST | `/models/{id}/approve` | action panel |
| POST | `/models/{id}/kill-switch` | emergency stop |
| POST | `/models/{id}/explain` | explain panel |

Note: `kill-switch` takes `reason` as a **query parameter**. The authenticated
Supabase user is recorded as the actor; the browser cannot supply or spoof a
`triggered_by` identity.

## Demo flow

1. Land on the portfolio — twenty-six models, four headline numbers, filter by risk.
2. Open **fraud-flagger** (high risk, score ~6.25). Pick "Live", submit. The UI
   warns you first, then the backend returns **403** with its own explanation.
3. Open a model in Testing. Notice "Live" is struck through — stages can't be
   skipped, and that's a **400**, a different failure from the score gate.
4. Open **sme-credit-scorer**. The metric chart shows the accuracy dip. The
   audit trail shows `drift-monitor-service` demoting it back to review, with a
   machine-written justification — an automated actor going through the same
   door a human would.
5. Scroll to "Explain a decision", raise the GST filing delay, re-run, and watch
   the ranked factors reorder.
6. Open the emergency stop. Note it's behind a disclosure, needs a documented
   reason, and lands in the audit trail flagged red.
