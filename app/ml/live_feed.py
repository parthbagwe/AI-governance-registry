"""
Live FX rate feed — real market data, refreshed every business day.

Why FX, in a project about banking AI:

Every bank with cross-border business carries currency exposure, and a market
risk desk watches it daily. Under the RBI's draft Model Risk Management
guidance, market risk models sit squarely inside the model inventory that has
to be governed — so an FX monitor is exactly the kind of model this registry
exists to supervise.

It's also the rare case where the real data is genuinely public. ECB reference
rates are published every business day, free, no key, no scraping. So unlike
the credit models in this portfolio — where customer-level data is private and
had to be simulated — this model runs on the same numbers a treasury desk
actually looks at.

What the model watches is a *day*, not a currency. One row per business day,
with features describing how the whole exposure basket behaved: how far the
worst mover went, whether currencies moved together or scattered, how many
crossed a materiality threshold. A treasury analyst doesn't ask "did EUR
move?" — they ask "was today a normal day?"

Source: https://api.frankfurter.dev (ECB reference rates, no key required).
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

API_ROOT = "https://api.frankfurter.dev/v1"

# Base currency: an Indian bank's book is denominated in INR.
BASE = "INR"

# The exposure basket. Chosen for India's actual trade and remittance
# corridors rather than for being the largest currencies globally — HKD, SGD
# and AED-adjacent flows matter here in a way they wouldn't for a US bank.
BASKET = ["USD", "EUR", "GBP", "JPY", "CHF", "SGD", "AUD", "CAD", "HKD", "CNY"]

# A daily move this size or larger is "material" — the threshold a desk would
# actually escalate on, not a statistical artefact.
MATERIAL_MOVE_PCT = 0.5

FEATURES = [
    "max_abs_move",     # how far the single worst mover went
    "mean_abs_move",    # how much the basket moved on average
    "dispersion",       # did currencies move together, or scatter?
    "usd_move",         # the dominant exposure, tracked on its own
    "n_material_moves", # how many currencies crossed the escalation threshold
    "basket_drift",     # signed: was INR broadly weakening or strengthening?
]

FEATURE_LABELS = {
    "max_abs_move": "Largest single-currency move (%)",
    "mean_abs_move": "Average move across the basket (%)",
    "dispersion": "Spread of moves — did currencies scatter? (%)",
    "usd_move": "USD/INR move (%)",
    "n_material_moves": f"Currencies moving more than {MATERIAL_MOVE_PCT}%",
    "basket_drift": "Net direction of the basket (%)",
}


def _get(path: str, params: dict | None = None, timeout: float = 20.0) -> dict:
    resp = requests.get(
        f"{API_ROOT}{path}",
        params=params,
        timeout=timeout,
        headers={"User-Agent": "ai-governance-registry/1.0 (portfolio project)"},
    )
    resp.raise_for_status()
    return resp.json()


def fetch_rates(start: date, end: date, quiet: bool = False) -> pd.DataFrame:
    """
    Daily ECB reference rates for the basket, as INR per unit of foreign
    currency — the direction a desk actually quotes, so a rise means the rupee
    weakened.

    The API returns business days only. Weekends and holidays simply aren't
    there, which is correct: there was no market, so there is no observation.
    Interpolating them would be inventing data.
    """
    if not quiet:
        print(f"📡 Fetching ECB rates {start} → {end} ({len(BASKET)} currencies)…")

    try:
        payload = _get(
            f"/{start.isoformat()}..{end.isoformat()}",
            {"base": BASE, "symbols": ",".join(BASKET)},
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not reach the FX feed at {API_ROOT}. "
            f"Check your internet connection or whether the host is blocked "
            f"on this network. Underlying error: {e}"
        ) from e

    rates = payload.get("rates", {})
    if not rates:
        raise RuntimeError(f"FX feed returned no rates for {start}..{end}.")

    # Response is {date: {ccy: rate}} where rate = foreign per 1 INR.
    # Inverted here to INR per foreign unit.
    df = pd.DataFrame(rates).T.sort_index()
    df.index = pd.to_datetime(df.index)
    df = df.apply(pd.to_numeric, errors="coerce")
    df = 1.0 / df

    # A currency occasionally goes missing for a single day. Carrying the last
    # observation forward is the honest fix — it says "no new information",
    # which is true. Any leading gap is dropped rather than back-filled.
    df = df.ffill().dropna()

    if not quiet:
        print(f"✅ {len(df)} business days of real market data.")
    return df


def engineer_features(rates: pd.DataFrame) -> pd.DataFrame:
    """
    Collapses the per-currency rate panel into one row per day describing how
    the basket as a whole behaved. The first row is dropped — you can't
    compute a change without a previous day to change from.
    """
    pct = rates.pct_change().mul(100).dropna(how="all")

    out = pd.DataFrame(index=pct.index)
    out["max_abs_move"] = pct.abs().max(axis=1)
    out["mean_abs_move"] = pct.abs().mean(axis=1)
    out["dispersion"] = pct.std(axis=1)
    out["usd_move"] = pct["USD"] if "USD" in pct.columns else 0.0
    out["n_material_moves"] = (pct.abs() >= MATERIAL_MOVE_PCT).sum(axis=1).astype(float)
    out["basket_drift"] = pct.mean(axis=1)

    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    out.insert(0, "observed_on", out.index.strftime("%Y-%m-%d"))
    return out.reset_index(drop=True)


def snapshot(start: date, end: date, quiet: bool = False) -> pd.DataFrame:
    """Fetch a window of real market data, feature-engineered and ready to score."""
    return engineer_features(fetch_rates(start, end, quiet=quiet))


# Window definitions, relative to whenever this is run. The baseline is
# deliberately cut off well before the present so the monitored window is
# genuinely unseen data rather than a slice of what the model trained on.
BASELINE_YEARS = 3
BASELINE_GAP_DAYS = 120   # baseline ends here-many days before today
CURRENT_WINDOW_DAYS = 120  # the recent window the monitor scores


def baseline_window(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return (
        today - timedelta(days=365 * BASELINE_YEARS),
        today - timedelta(days=BASELINE_GAP_DAYS),
    )


def current_window(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return (today - timedelta(days=CURRENT_WINDOW_DAYS), today)


if __name__ == "__main__":
    start, end = baseline_window()
    df = snapshot(start, end)
    df.to_csv("live_baseline.csv", index=False)

    print(f"\n📊 What a normal FX day has looked like ({start} → {end}):")
    print(df[FEATURES].describe().round(3).to_string())
    print(f"\n✅ {len(df)} business days saved to live_baseline.csv")
    print("   Next: python -m app.ml.train_live_model")
