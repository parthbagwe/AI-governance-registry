"""
Live payment-transaction feed.

Why a public blockchain, in a project about *banking* AI:

Real cross-border payment traffic (SWIFT, RTGS, card rails) is private. There
is no public, live feed of it, and there never will be — it's customer
financial data. But a public blockchain is a genuinely live, legally
observable settlement ledger: real value moving between real parties, right
now, with fees and transaction structure visible to anyone.

So it's used here as a *stand-in* for the kind of payment stream a bank's
AML/fraud team monitors. The point isn't the asset class — it's that the
monitoring loop runs against data that is actually arriving, continuously,
rather than replaying a CSV and calling it "production traffic". Everything
downstream (scoring, drift, auto-demotion) is identical to what you'd wire up
against a real payment rail.

Source: mempool.space public API. No key, no auth, documented and free.
Endpoint used: GET /api/mempool/recent -> a page of transactions currently
waiting to settle, each with {txid, fee, vsize, value}.
"""

import time

import numpy as np
import pandas as pd
import requests

RECENT_URL = "https://mempool.space/api/mempool/recent"

# The engineered features the anomaly model actually sees. Each one is a
# recognised signal in payment monitoring, not just an available number:
FEATURES = [
    "log_value",       # order of magnitude of the payment
    "log_fee",         # order of magnitude of what was paid to move it
    "vsize",           # transaction complexity — a proxy for how many
                       # sources were combined, which is how structuring shows up
    "fee_rate",        # fee per byte: the "urgency premium" the sender paid
    "fee_ratio_bps",   # fee as basis points of the payment itself — paying
                       # 500bps to move money is behaviour worth a second look
]

FEATURE_LABELS = {
    "log_value": "Payment size (order of magnitude)",
    "log_fee": "Fee paid (order of magnitude)",
    "vsize": "Transaction complexity",
    "fee_rate": "Urgency premium (fee per byte)",
    "fee_ratio_bps": "Fee as a share of the payment (bps)",
}


def _poll_once(timeout: float = 10.0) -> list[dict]:
    """One page of live pending transactions. Raises on a non-200."""
    resp = requests.get(
        RECENT_URL,
        timeout=timeout,
        headers={"User-Agent": "ai-governance-registry/1.0 (portfolio project)"},
    )
    resp.raise_for_status()
    return resp.json()


def fetch_live_transactions(polls: int, delay: float = 1.2, quiet: bool = False) -> pd.DataFrame:
    """
    Polls the live endpoint `polls` times, deduplicating by txid.

    Each page only returns ~10 transactions, but the pending pool turns over
    constantly, so repeated polls yield fresh ones. The delay is deliberate:
    this is a free public service and hammering it would be rude, as well as
    getting us rate-limited.
    """
    seen: dict[str, dict] = {}
    failures = 0

    for i in range(polls):
        try:
            for tx in _poll_once():
                seen[tx["txid"]] = tx
        except Exception as e:  # network blips shouldn't kill a monitoring run
            failures += 1
            if not quiet:
                print(f"  poll {i + 1}/{polls} failed ({e.__class__.__name__}) — continuing")
            if failures >= max(3, polls // 2):
                raise RuntimeError(
                    f"Live feed unreachable after {failures} failures. "
                    f"Check your internet connection, or whether {RECENT_URL} is up."
                ) from e

        if not quiet and (i + 1) % 10 == 0:
            print(f"  polled {i + 1}/{polls} — {len(seen)} unique transactions so far")

        if i < polls - 1:
            time.sleep(delay)

    if not seen:
        raise RuntimeError("Live feed returned no transactions at all.")

    return pd.DataFrame(list(seen.values()))


def engineer_features(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Turns the raw {txid, fee, vsize, value} rows into the modelling features.

    Values are floored at 1 before any division or log — a transaction can
    legitimately report a zero value, and one divide-by-zero shouldn't poison
    an entire monitoring batch.
    """
    df = raw.copy()

    value = np.maximum(df["value"].astype(float), 1.0)
    fee = np.maximum(df["fee"].astype(float), 1.0)
    vsize = np.maximum(df["vsize"].astype(float), 1.0)

    df["log_value"] = np.log10(value)
    df["log_fee"] = np.log10(fee)
    df["vsize"] = vsize
    df["fee_rate"] = fee / vsize
    df["fee_ratio_bps"] = (fee / value) * 10_000

    # A handful of transactions carry absurd fee ratios (dust, consolidation
    # sweeps). Clipping keeps one outlier from dominating the feature scale
    # without discarding the row — it's still flagged, just not allowed to
    # rewrite what "normal" looks like for everything else.
    df["fee_ratio_bps"] = df["fee_ratio_bps"].clip(upper=100_000)

    return df[["txid", "value", "fee", *FEATURES]]


def snapshot(polls: int, quiet: bool = False) -> pd.DataFrame:
    """Fetch a live batch and return it feature-engineered, ready to score."""
    if not quiet:
        print(f"📡 Pulling a live batch from {RECENT_URL} ({polls} polls)…")
    raw = fetch_live_transactions(polls, quiet=quiet)
    df = engineer_features(raw)
    if not quiet:
        print(f"✅ {len(df)} unique live transactions captured.")
    return df


if __name__ == "__main__":
    # Builds the reference snapshot the anomaly model trains on. Roughly
    # 90 seconds of live traffic, which is enough to characterise "normal".
    df = snapshot(polls=60)
    df.to_csv("live_baseline.csv", index=False)

    print("\n📊 What normal looks like right now:")
    print(df[FEATURES].describe().round(2).to_string())
    print("\n✅ Saved to live_baseline.csv")
