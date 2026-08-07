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
| `fx-intraday-monitor` | **Live and real** — 1-minute USD/INR bars from Twelve Data, fetched at monitoring time | Genuine market microstructure. Every run sees minutes that did not exist on the previous run, and reports how many |
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
| Medium | 7.0 | Daily FX exposure monitoring, lead-scoring |
| High | 8.5 | Credit decisions, fraud blocking, intraday FX |

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
pip install -r requirements-dev.txt
```

`requirements.txt` holds only what the deployed API needs. `requirements-dev.txt`
adds training, drift detection, the live feeds and the Streamlit dashboard —
that's the one to install locally.

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

python -m app.ml.intraday_feed          # 1000 real 1-minute USD/INR bars
python -m app.ml.train_intraday_model
python -m app.ml.register_intraday_model
python -m app.ml.intraday_monitor       # re-run any time — watch it climb
```

The intraday model needs a free Twelve Data API key. Copy `.env.example` to
`.env` and paste it in; `.env` is gitignored.

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

**What the daily FX model watches.** One row per business day, not per
currency — because a treasury analyst doesn't ask "did EUR move?", they ask
"was today a normal day?" The six features describe how the whole INR exposure
basket behaved: how far the worst mover went, whether currencies moved
together or scattered, how many crossed a 0.5% materiality threshold, and the
net direction of the basket.

---

## Two models, one market, different governance

`fx-exposure-monitor` and `fx-intraday-monitor` watch the same currency,
are owned by the same team, and use the same algorithm. One is tiered
**medium**, the other **high**.

The difference isn't technical. The daily model's output lands on an analyst's
desk the next morning — a person stands between the model and any action. The
1-minute model is fast enough to feed automated hedging, so its output can move
money with nobody in the loop. **Removing the human is what raises the tier.**

The consequence is mechanical and visible in the registry: the intraday model
needs 8.5 to reach production where its daily sibling needs 7.0. The faster
model faces the stricter bar, which is the right way round.

This is the clearest illustration in the project of what risk tiering is
actually for. It isn't a label describing how clever the model is — it's a
statement about the blast radius of being wrong, and how much human judgement
sits between the output and the consequence.

The same logic sets the alert budgets. Contamination is 2% on the daily model
and 1% on the intraday one. At daily cadence 2% is roughly five alerts a year;
at 1-minute cadence it would be about fourteen an hour. Nobody reads fourteen
alerts an hour — they mute the channel, and then the one that mattered goes
unseen. That number is an operational decision, not a hyperparameter.

### Proving the data is live

`intraday_monitor` reports, every run, how many of the bars it just fetched did
not exist when the baseline was captured:

```
🔴 7 of 200 bars are new since the baseline was captured.
   Most recent bar: 2026-08-06 03:08:00 UTC at 95.08653
```

Run it again five minutes later and that number climbs. Against a replayed CSV
it would be zero, forever. It's logged to the registry as
`new_bars_since_baseline`, so liveness accumulates on the dashboard chart
rather than being something you have to assert.

The blunter demo: turn off your wifi and run it. It fails with a connection
error. A file-reading script wouldn't notice.

### A limitation worth naming

FX has strong intraday seasonality. USD/INR at 02:00 UTC is a different market
from USD/INR at 12:30 — thinner book, smaller moves. The first version of this
model didn't know that, so it called every quiet overnight minute normal and
every busy London minute an anomaly.

The fix was cyclical time-of-day features (sine/cosine of the hour, so 23:59
and 00:01 come out adjacent rather than 23 apart). The model now asks the right
question: *was this minute unusual for this time of day?*

Those features are deliberately excluded from the drift comparison. A monitored
window spans a few hours and the baseline spans a full day, so the clock
differs between them by construction, on every run. Including it would mean
permanently reporting drift for the sole reason that time passed — and a
detector that fires unconditionally tells you nothing.

**Still outstanding:** drift is measured against the whole baseline rather than
against matching hours of the day, so a window drawn entirely from the quiet
Asian session will report some drift that is really session composition. The
monitor prints a warning when the window is short enough for this to bite.
Restricting the baseline to comparable hours is the honest fix, and it isn't
built yet.

---

## Deployment

The backend goes to Render and the frontend to Vercel, because they need
different things: FastAPI wants a long-running process, and Next.js compiles to
static output plus serverless functions. Vercel can't host the first;
that's why Streamlit was replaced rather than lifted across.

### 1. Backend on Render

The repo includes `render.yaml`, so this is a Blueprint deploy rather than a
form-filling exercise:

1. Push to GitHub.
2. Render -> **New** -> **Blueprint** -> select this repo.
3. It provisions a free Postgres and the web service, and wires `DATABASE_URL`
   between them automatically.
4. Wait for the build. The first one takes several minutes — `shap` and
   `xgboost` are large.

When it's up, check `https://<your-service>.onrender.com/health`. It reports
which database backend is actually in use:

```json
{ "status": "ok", "database": "postgresql", "persistent": true }
```

If that says `sqlite` and `persistent: false`, `DATABASE_URL` didn't reach the
service. Everything will appear to work and then quietly lose all data on the
next redeploy — which is precisely why the health check reports it rather than
just saying "ok".

`bootstrap.py` runs before the server starts. It creates tables and seeds the
sample portfolio **only if the registry is empty**, so redeploys never wipe
data.

### 2. Frontend on Vercel

1. Vercel -> **Add New** -> **Project** -> import the repo.
2. Set **Root Directory** to `frontend`. Everything else is detected.
3. Add an environment variable:
   `NEXT_PUBLIC_API_URL = https://<your-service>.onrender.com/api/v1`
   — the `/api/v1` suffix matters; without it every request 404s.
4. Deploy.

### 3. Close the CORS hole

Back on Render, set `ALLOWED_ORIGINS` to your Vercel URL and redeploy. It
defaults to `*` so a fresh clone runs with no configuration, but a governance
API that any page on the internet can POST approvals to is not a governance
API.

### 4. Point the monitors at production

The monitors talked to the registry in-process, which assumed the API and the
monitor were the same program. Set `REGISTRY_API_URL` and they speak to the
deployed service over HTTP instead:

```powershell
$env:REGISTRY_API_URL = "https://<your-service>.onrender.com"
python -m app.ml.intraday_monitor
```

Every script prints where it's writing before it does anything — *which
registry did I just update?* should never be something you have to work out
afterwards.

Nothing else changes. Both paths hit the same endpoints, the same state
machine, and get the same 403 when a promotion is refused. A monitor running
against production has no more authority than one running locally, which is
the same principle the governance gate rests on: no actor gets a private door.

### Things that will catch you out

- **Free Render services sleep** after ~15 minutes idle. The first request
  after a quiet spell takes 30–60 seconds. Load the page a minute before you
  demo it.
- **`sme_credit_model.pkl` is committed**, against the general rule about not
  committing build outputs. `/explain` loads it at request time and a hosted
  instance has no way to train one. A real setup would pull it from a model
  registry or object store; this is a documented shortcut, and the endpoint
  returns a clear 503 rather than a 500 if the artifact is missing.
- **The monitors run from your machine, not Render.** Free tier has no cron.
  For a real deployment they'd be a scheduled job — GitHub Actions on a cron
  hitting the deployed API would work and stay free.
- **`NEXT_PUBLIC_` variables are compiled into the browser bundle.** Fine for
  an API URL, never for a secret.

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
6. **Live data.** Open `fx-intraday-monitor` — the lineage panel shows a
   pulsing live-feed badge with the actual endpoint. Run
   `python -m app.ml.intraday_monitor`, wait five minutes, run it again:
   the new-bar count climbs, and the chart grows.
7. **Same market, different governance.** Put `fx-exposure-monitor` and
   `fx-intraday-monitor` side by side. Same currency, same team, same
   algorithm — but one needs 7.0 to go live and the other needs 8.5, because
   only one of them has a human between its output and the money.
8. **Emergency stop.** Behind a disclosure, requires a documented reason, lands
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
- **Tiering has to mean something.** The daily FX monitor is tiered *medium*,
  not high, even though it would have been easy to inflate. It moves the bank's
  own book and desk attention, not a customer's access to their money. If
  everything is high-risk, the tier carries no information.
- **The model found a real crisis, unsupervised.** The top-flagged day in
  three years of ECB data was **5 August 2024** — worst mover 5.22%, all ten
  currencies breaching the materiality threshold. That's the yen carry-trade
  unwind, the day the Nikkei fell 12% and the VIX spiked above 60. Nobody told
  the model what a market shock looks like or when one happened; it learned the
  shape of an ordinary day and that one didn't fit. When an interviewer asks
  whether the model works, this is the answer — not a metric, a date they'll
  recognise.
- **A real finding from the data.** The intraday model's flagged minutes
  clustered into a single hour — 12:27 to 13:27 UTC, the London/Europe
  overlap — without anyone telling it when the sessions are. Two adjacent
  minutes went +30.6 bps and then −29.4 bps: a spike and full reversal inside
  two minutes, which is a liquidity event, someone hitting a thin book. The
  model found it unsupervised.
- **A registry that let you register the same thing twice.** Re-running a
  registration script created a *second* `fx-intraday-monitor v1.0.0` with a
  different ID — because nothing enforced uniqueness on (name, version). Two
  rows claiming to be the same version means the registry can't answer which
  one is live, and each accumulates its own separate approval history. Fixed
  with a database constraint plus a 409 from the API, so it holds even against
  something writing to the DB directly. For a system whose entire job is
  knowing what models exist, this was the worst possible bug to have.
- **A metric that wasn't measuring anything.** Training the anomaly models
  logged `anomaly_rate`, and it came back as 1.03% every time, on different
  data. It had to: Isolation Forest's `contamination` parameter *defines* the
  flag rate on the training set, so that metric could only ever hand back the
  setting it was given. It's now `baseline_flag_rate`, kept distinct from the
  anomaly rate the monitor observes on unseen data — which is free to move, and
  therefore actually tells you something.
- **Reading the drift output critically.** The first monitoring run reported
  50% drift on a window that was almost entirely *inside* the baseline. That
  isn't a bug — it's intraday seasonality, and chasing it led to the
  time-of-day features and the drift/model feature split described above.
  Noticing that a green-looking number was measuring the wrong thing mattered
  more than the fix.

---

## Not yet built

- Docker Compose to start everything with one command
- MLflow for experiment tracking instead of pickle files
- Scheduled monitoring in the cloud — the monitors can target the deployed
  registry, but something still has to run them on a timer
- Alembic migrations. `create_all` builds missing tables but won't alter
  existing ones, so a schema change currently means rebuilding the database
- Authenticated identity — `approved_by` is free text, not a verified user
- Role-based segregation of duties (three lines of defence) — designed, not
  yet enforced end to end
- Session-matched drift comparison for the intraday model (see "A limitation
  worth naming" above)
