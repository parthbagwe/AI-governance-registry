"""
Intraday FX feed — 1-minute USD/INR bars from Twelve Data.

Why a *second* FX model, when fx-exposure-monitor already watches this market:

Because they are governed differently, and that difference is the interesting
part. The daily model produces a number a treasury analyst reads the next
morning; a human sits between its output and any action. An intraday monitor
running on 1-minute bars is fast enough to feed automated hedging, which means
its output can move money with nobody in the loop.

Same market, same underlying signal — but the absence of a human reviewer is
precisely what pushes the intraday version into a higher risk tier. That's not
a technical distinction, it's a governance one, and it's the kind of judgement
a model risk framework exists to make.

Data: Twelve Data (https://twelvedata.com), free tier, 800 credits/day.
Each call here costs 1 credit, so a monitor run every few minutes is
comfortably within budget.

Setup — the key must never be committed:

    PowerShell (this session only):
        $env:TWELVEDATA_API_KEY = "your-key"

    Or, permanently, create a file called `.env` in the project root:
        TWELVEDATA_API_KEY=your-key

`.env` is gitignored. Nothing here writes the key to disk or logs it.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

API_URL = "https://api.twelvedata.com/time_series"

SYMBOL = "USD/INR"
INTERVAL = "1min"

# Rolling window used to judge whether a bar's range is unusual *relative to
# recent conditions* rather than to some fixed threshold. Volatility regimes
# shift through a session; 30 minutes of context keeps the comparison fair.
RECENT_WINDOW = 30

FEATURES = [
    "return_bps",       # signed move, in basis points
    "abs_return_bps",   # magnitude, independent of direction
    "range_bps",        # high-to-low travel within the minute
    "gap_bps",          # jump between one bar's close and the next bar's open
    "body_ratio",       # how much of the range was directional vs. wick
    "range_vs_recent",  # this bar's range against the last 30 minutes
]

FEATURE_LABELS = {
    "return_bps": "Price move over the minute (bps)",
    "abs_return_bps": "Size of the move, ignoring direction (bps)",
    "range_bps": "High-to-low travel within the minute (bps)",
    "gap_bps": "Jump since the previous minute's close (bps)",
    "body_ratio": "Directional share of the move (0 = pure wick, 1 = clean trend)",
    "range_vs_recent": "This minute's range vs the last 30 minutes",
}


def _load_api_key() -> str:
    """
    Environment variable first, then a `.env` file in the project root.

    Parsed by hand rather than pulling in python-dotenv — it's six lines, and
    one fewer dependency in a project that already has plenty.
    """
    key = os.environ.get("TWELVEDATA_API_KEY")
    if key:
        return key.strip()

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "TWELVEDATA_API_KEY":
                return value.strip().strip('"').strip("'")

    raise RuntimeError(
        "No Twelve Data API key found.\n"
        "  Set it for this terminal:  $env:TWELVEDATA_API_KEY = \"your-key\"\n"
        "  Or create a .env file in the project root containing:\n"
        "      TWELVEDATA_API_KEY=your-key\n"
        "  Free key: https://twelvedata.com/pricing"
    )


def fetch_bars(outputsize: int = 1000, quiet: bool = False) -> pd.DataFrame:
    """
    Most recent `outputsize` one-minute bars, oldest first.

    The API returns newest-first with prices as strings and no volume field
    (correct for spot FX — there's no central exchange to report it). Both are
    normalised here so nothing downstream has to know about the wire format.
    """
    if not quiet:
        print(f"📡 Fetching {outputsize} × {INTERVAL} {SYMBOL} bars from Twelve Data…")

    try:
        resp = requests.get(
            API_URL,
            params={
                "symbol": SYMBOL,
                "interval": INTERVAL,
                "outputsize": outputsize,
                "apikey": _load_api_key(),
            },
            timeout=25,
            headers={"User-Agent": "ai-governance-registry/1.0 (portfolio project)"},
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(
            f"Could not reach Twelve Data. Check your connection, or whether "
            f"the host is blocked on this network. Underlying error: {e}"
        ) from e

    # The API returns HTTP 200 even for rejected requests, signalling failure
    # in the body instead — so the status field has to be checked explicitly.
    if payload.get("status") != "ok":
        raise RuntimeError(
            f"Twelve Data rejected the request: "
            f"{payload.get('message', payload)}\n"
            f"Common causes: an invalid key, or the free tier's daily credit "
            f"limit (800/day) being exhausted."
        )

    values = payload.get("values") or []
    if not values:
        raise RuntimeError("Twelve Data returned no bars.")

    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.sort_values("datetime").reset_index(drop=True)

    if not quiet:
        print(f"✅ {len(df)} bars, {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]} (UTC)")
    return df


def engineer_features(bars: pd.DataFrame) -> pd.DataFrame:
    """
    Turns OHLC bars into microstructure features.

    Everything is expressed in basis points rather than raw price, so the
    features stay meaningful if the pair ever re-rates — a model trained at
    83 rupees to the dollar shouldn't silently break at 95.
    """
    df = bars.copy()

    prev_close = df["close"].shift(1)
    open_ = df["open"].replace(0, np.nan)

    df["return_bps"] = (df["close"] / prev_close - 1.0) * 10_000
    df["abs_return_bps"] = df["return_bps"].abs()
    df["range_bps"] = ((df["high"] - df["low"]) / open_) * 10_000
    df["gap_bps"] = (df["open"] / prev_close - 1.0) * 10_000

    # A bar that travels a long way but closes near where it opened is a wick:
    # a liquidity air-pocket someone traded through and the market recovered.
    # A bar whose body fills its range is a genuine directional move. Very
    # different events, identical if you only look at the range.
    span = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_ratio"] = ((df["close"] - df["open"]).abs() / span).fillna(0.0)

    recent = df["range_bps"].rolling(RECENT_WINDOW, min_periods=RECENT_WINDOW).median()
    df["range_vs_recent"] = df["range_bps"] / recent.replace(0, np.nan)

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)

    out = df[["datetime", "close", *FEATURES]].copy()
    out["observed_at"] = out["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out.drop(columns=["datetime"]).reset_index(drop=True)


def snapshot(outputsize: int = 1000, quiet: bool = False) -> pd.DataFrame:
    """Fetch and feature-engineer the latest bars, ready to score."""
    return engineer_features(fetch_bars(outputsize, quiet=quiet))


BASELINE_PATH = "intraday_baseline.csv"


if __name__ == "__main__":
    df = snapshot(outputsize=1000)
    df.to_csv(BASELINE_PATH, index=False)

    print(f"\n📊 What a normal minute has looked like ({len(df)} bars):")
    print(df[FEATURES].describe().round(3).to_string())
    print(f"\n   Latest price: {df['close'].iloc[-1]:.5f} at {df['observed_at'].iloc[-1]} UTC")
    print(f"\n✅ Saved to {BASELINE_PATH}")
    print("   Next: python -m app.ml.train_intraday_model")
