# AI Model Governance Registry

A working governance layer for a bank's AI model portfolio. It tracks models
through a **pilot -> review -> production -> retired** lifecycle, gates
promotion behind a risk-tiered scorecard, keeps an append-only audit trail of
every decision, and automatically pulls a live model back for review when the
data underneath it shifts.

It is deliberately **not** another credit or fraud model. It's the system that
decides whether such a model is allowed to run at all.

---

## Why this exists

Most banking-AI portfolio projects stop at "I trained a fraud classifier."
That's necessary, but it isn't what actually blocks AI adoption inside a
regulated bank.

- **Axis Bank** is the only ISO 42001-certified BFSI organisation globally
  (the first international standard for an AI Management System), and its
  AXIOM programme evaluates every AI use case on five dimensions — efficiency,
  adoption, input quality, cost reduction, revenue — before it may move from
  pilot to production.
- **ICICI** runs AI across underwriting, next-best-offer, and fraud detection
  at a scale where *governing* dozens of live models is harder than training
  any single one.
- The **RBI's June 2026 draft Guidance on Regulatory Principles for Model Risk
  Management** mandates a comprehensive model inventory, risk-based tiering,
  explainability over black-box AI, and an override/suspension mechanism — a
  kill switch — that works independently of routine approval workflow.

This project implements those specific requirements at small scale, by name.

> The RBI guidance was a **draft**, with public comments invited to July 2026.
> Building against a draft is intentional: it's the difference between reading
> where regulation is going and waiting to be told.

---

## Data provenance — read this before judging the models

Different parts of this system use different kinds of data, for reasons worth
stating plainly rather than glossing over.

| Model | Data | Why |
|---|---|---|
| `fx-exposure-monitor` | **Live and real** — ECB daily reference rates, fetched at monitoring time | The rare case where the genuinely useful data is public. These are the same rates a treasury desk works from. No simulation anywhere in this model |
| `personal-loan-credit-scorer` | **Real, static** — Kaggle "Give Me Some Credit" (2011 competition), ~150k anonymised borrowers | A real, well-known public credit benchmark. Real signal, real default labels |
| `sme-credit-scorer` | **Synthetic**, with deliberately engineered correlations | GST filing records are not public anywhere. Simulating them is the only responsible option — not a shortcut |
| 7 other registry entries | **Metadata only** — no trained model behind them | They exist to make the portfolio realistic in shape. A bank's registry is mostly entries you aren't personally training |
| The registry itself (approvals, scorecards, lineage) | **Synthetic**, necessarily | No bank publishes its internal AI governance data. There is no honest alternative here |

The governance layer doesn't care which of these it's pointed at. That's the
argument: the rules are identical whether the data below them is live, real,
or simulated.

---

## Architecture

```
  Next.js frontend            Streamlit dashboard
  (TypeScript, Vercel)        (legacy, still works)
            |                          |
            +------------+-------------+
                         v
              +----------------------+        +--------------------+
              |  FastAPI REST API    |------->|  SQLite / Postgres |
              |  + app/workflow.py   |        |  (governance.db)   |
              |  state machine,      |        +--------------------+
              |  risk-tiered gate,   |
              |  kill switch         |
              +----------+-----------+
                         ^
       +-----------------+-----------------+
       |                 |                 |
  ML training      Drift monitor      Live FX monitor
  (XGBoost,        (Evidently AI)     (pulls real rates,
   Isolation                           scores, auto-demotes)
   Forest)
```

**The one design principle that matters:** every path into the system — the web
UI, the Streamlit dashboard, the drift monitor, the live monitor — goes through
the *same* `/approve` endpoint and the *same* rules in `app/workflow.py`. There
is no side channel, and automated actors get no bypass. A robot demotion and a
human demotion leave the same kind of audit record; only the name differs.

---

## Governance rules

**Legal stage transitions:**

| From | Can move to |
|---|---|
| `pilot` | `review`, `deprecated` |
| `review` | `production` *(score-gated)*, `pilot`, `deprecated` |
| `production` | `review`, `deprecated` |
| `deprecated` | *terminal — no way out* |

**Risk-tiered promotion bar.** The governance score required to reach
production scales with how much the model's output can affect a customer's
money or the bank's compliance position:

| Risk tier | Minimum score | Example |
|---|---|---|
| Low | 5.0 | Internal FAQ bot |
| Medium | 7.0 | FX exposure monitoring, lead-scoring |
| High | 8.5 | Credit decisions, fraud blocking |

The governance score is the average of five 0-10 dimensions. A model with any
dimension unscored, or an average below its tier's bar, is **mechanically
blocked** from production regardless of who submits the request.

**Kill switch.** A separate endpoint that deactivates a model from *any* stage,
with no score check and no respect for the transition map, requiring a
documented reason and permanently flagged as an emergency in the audit trail.
Deliberately not a parameter on `/approve` — an emergency stop should not be
reachable by the same form a routine reviewer fills in.

---

## Setup

```powershell
cd D:\ai-governance-registry
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Frontend (needs Node.js LTS):

```powershell
cd frontend
npm install
copy .env.local.example .env.local
```

---

## Running it

**Terminal 1 — API:**

```powershell
python seed.py                              # creates DB + sample portfolio
python -m uvicorn app.main:app --reload
```
Verify at http://localhost:8000/docs

**Terminal 2 — frontend:**

```powershell
cd frontend
npm run dev
```
Opens at http://localhost:3000

**Terminal 3 — the ML pipeline** (one-time, in order):

```powershell
python -m app.ml.generate_data          # synthetic SME data
python -m app.ml.train_model            # XGBoost SME credit scorer
python -m app.ml.log_metrics
python -m app.ml.fairness_check         # disparate-impact test
python -m app.ml.drift_check            # Evidently -> auto-demotion

python -m app.ml.prepare_real_data      # real Kaggle credit data
python -m app.ml.register_personal_model

python -m app.ml.live_feed              # 3 years of real ECB rates
python -m app.ml.train_live_model       # Isolation Forest on real market data
python -m app.ml.register_live_model
python -m app.ml.live_monitor           # re-run any business day for fresh data
```

The Streamlit dashboard still works if you prefer it:
`streamlit run app/dashboard/app.py`

---

## The live monitoring loop

`app/ml/live_monitor.py` is what makes the registry self-updating rather than a
static snapshot. Each run:

1. Pulls the most recent window of **real ECB reference rates**. Not a replay —
   every business day adds an observation that did not exist before.
2. Scores those days with the deployed Isolation Forest.
3. Logs the real observed anomaly rate and score distribution to the registry.
4. Runs Evidently drift detection against the baseline period, answering "does
   the current market regime still resemble the one this model learned?"
5. If enough features have drifted and the model is live, demotes it through
   the same `/approve` endpoint a human would use.

Run it on a schedule and the registry maintains itself:

```powershell
# Windows Task Scheduler, or:
python -m app.ml.live_monitor
```

Because the market genuinely moves between runs, the metric chart fills with
real measurements over time rather than seeded values — and a demotion, when it
happens, was caused by something that actually occurred in the market.

**What the FX model watches.** One row per business day, not per currency —
because a treasury analyst doesn't ask "did EUR move?", they ask "was today a
normal day?" The six features describe how the whole INR exposure basket
behaved: how far the worst mover went, whether currencies moved together or
scattered, how many crossed a 0.5% materiality threshold, and the net
direction of the basket.

---

## Demo script

1. **Portfolio page** — ten models, four headline numbers, filterable by risk
   tier and stage.
2. **Try to break it.** Open `fraud-flagger` (high risk, score ~6.25), pick
   "Live", submit. The UI warns you first; the backend then returns **403**
   with its own explanation. This is the core feature working.
3. **A different failure.** Open a model in Testing — "Live" is struck through.
   Skipping stages is a **400**, not a 403. Two independent defences.
4. **The whole story on one screen.** Open `sme-credit-scorer`: the metric
   chart shows the accuracy dip, and the audit trail shows
   `drift-monitor-service` demoting it back to review with a machine-written
   justification.
5. **No black boxes.** Scroll to "Explain a decision", raise the GST filing
   delay, re-run — the ranked factors reorder.
6. **Live data.** Open `fx-exposure-monitor` — the lineage panel shows a
   pulsing live-feed badge with the actual endpoint. Run
   `python -m app.ml.live_monitor` and refresh: new measurements appear,
   computed from rates published this week.
7. **Emergency stop.** Behind a disclosure, requires a documented reason, lands
   in the audit trail flagged red.

---

## Talking points

- **The bug worth admitting.** The state machine originally only allowed
  `production -> deprecated`. Wiring up the drift monitor exposed the gap: a
  drifted model needs demoting back to review, not killing outright. Finding
  and fixing that is part of the work, not a flaw to hide.
- **Risk tiering changed an answer.** Under a flat 7.0 bar, the SME credit
  model at 8.36 was fine. Under RBI-style tiering it's high-risk and faces 8.5
  — so it now correctly *fails*. The rule change caught something the old rule
  missed.
- **Honest metrics.** The SME model reports AUC ~0.68 on synthetic data; the
  real Kaggle model lands near 0.86. Credit models genuinely live in that
  range. A suspiciously perfect AUC is a red flag to anyone who's seen real
  credit data.
- **Class imbalance handled deliberately.** `scale_pos_weight` on the XGBoost
  models — without it, the classifier just learns to predict "no default" and
  looks falsely accurate.
- **Unsupervised where labels don't exist.** The FX monitor is an Isolation
  Forest because there's no labelled set of "days a desk should have
  escalated" — that label only exists in hindsight. Its contamination rate is
  an alert-volume decision, not a tuning knob: set it too high and analysts
  drown in noise, and the real alerts get ignored.
- **Tiering has to mean something.** The FX monitor is tiered *medium*, not
  high, even though it would have been easy to inflate. It moves the bank's own
  book and desk attention, not a customer's access to their money. If
  everything is high-risk, the tier carries no information.

---

## Not yet built

- Docker Compose to start everything with one command
- MLflow for experiment tracking instead of pickle files
- Postgres in place of SQLite (`app/database.py` reads `DATABASE_URL`, so this
  is a config change, not a rewrite)
- Authenticated identity — `approved_by` is free text, not a verified user
- Role-based segregation of duties (three lines of defence) — designed, not
  yet enforced end to end
