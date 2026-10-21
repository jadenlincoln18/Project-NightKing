"""The (bracket, minute) quote + settlement panel §1B scores against.

This module builds everything §1B's unit of observation needs **except the fit**:

    event_id, ticker, ts, bid, ask, settled_yes

It deliberately stops there. `fit_mean`, `fit_lo` and `fit_hi` are the three
remaining `disagree.REQUIRED_COLUMNS`, and they are not constructible for the
§1A universe from anything in this repository — see `FINDINGS_PHASE05.md` §3.
Building the panel anyway is useful: it is the half of the join that *is*
determined, it measures the N at every cut so the gate's power is known, and it
is what a fit would plug into the moment one exists.

Reads only the staged historical store under `data/_import/`. `ladder.store` is
imported read-only; `ladder/` is never modified.

Settlement comes from the store's own `kalshi_markets` table, not the discovery
snapshot: the snapshot is the narrower source and would silently discard most
events (`FINDINGS_PHASE05.md` §2, "Note on the settlement source").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from phase05 import stores

# Kalshi `result` values that constitute a settled binary outcome.
RESULT_YES = "yes"
RESULT_NO = "no"
PANEL_COLUMNS = ("event_id", "ticker", "ts", "bid", "ask", "settled_yes")


def _load_ladder_store():
    stores.add_repo_to_path()
    from ladder import store as lstore  # read-only reuse
    return lstore


def settlement_map(markets: pd.DataFrame) -> dict:
    """ticker -> 1.0 / 0.0 for markets with a binary settled result, else absent.

    Markets still `active`, or carrying an empty/again non-binary `result`, are
    omitted rather than defaulted. A missing settlement must drop the row, never
    become a zero: a silent zero would score every unsettled bracket as a
    realised NO and bias the Brier comparison toward whichever forecast is
    lower.
    """
    out = {}
    for t, r in zip(markets["ticker"], markets["result"]):
        if r == RESULT_YES:
            out[t] = 1.0
        elif r == RESULT_NO:
            out[t] = 0.0
    return out


def event_panel(series: str, event: str, info, markets: pd.DataFrame,
                root, lstore, every: int = 1) -> pd.DataFrame | None:
    """One settled ladder -> tidy (bracket, minute) rows with quotes and outcome.

    `every` subsamples the minute grid (1 = every minute, §1B's stated unit).
    Returns None when the event has no candles or no settled bracket.
    """
    candles = lstore.load_event_candles(series, event, root=root)
    if candles is None or candles.empty:
        return None
    grid = lstore.build_grid(candles, info)
    if grid is None:
        return None

    settle = settlement_map(markets)
    tickers = list(info["tickers"])
    keep = [i for i, t in enumerate(tickers) if t in settle]
    if not keep:
        return None

    rows_idx = np.arange(0, grid.bid.shape[0], max(1, int(every)))
    bid = grid.bid[np.ix_(rows_idx, keep)]
    ask = grid.ask[np.ix_(rows_idx, keep)]
    ts = grid.ts[rows_idx]

    n_min, n_br = bid.shape
    kept_tickers = [tickers[i] for i in keep]
    out = pd.DataFrame({
        "event_id": event,
        "ticker": np.repeat(kept_tickers, n_min),
        "ts": np.tile(ts, n_br),
        "bid": bid.T.reshape(-1),
        "ask": ask.T.reshape(-1),
    })
    out["settled_yes"] = out["ticker"].map(settle).astype(float)
    # A minute with no quote on either side carries no information for §1B's
    # two-sided executable filter; drop it here to keep the panel small.
    out = out[out["bid"].notna() | out["ask"].notna()]
    return out.reset_index(drop=True)


def series_panel(series: str, root=None, every: int = 1, max_events: int | None = None):
    """Panel for one series, plus the per-series cut counts.

    Cut counts are returned rather than printed because §1B requires the N at
    every stage to be reportable.
    """
    lstore = _load_ladder_store()
    root = stores.check_staging(root)
    stores.assert_not_live(root)

    markets = lstore.load_markets([series], root=root)
    cuts = {"series": series, "markets": len(markets),
            "events": int(markets["event_ticker"].nunique()) if len(markets) else 0}
    if markets.empty:
        return pd.DataFrame(columns=list(PANEL_COLUMNS)), cuts

    events = lstore.events_table(markets, root=root)
    cuts["events_classified"] = len(events)
    cuts["events_other"] = int((events["kind"] == "other").sum())
    usable = events[(events["kind"] != "other") & events["has_candles"]]
    cuts["events_with_candles"] = len(usable)

    settle = settlement_map(markets)
    cuts["markets_settled"] = len(settle)

    parts, n_used = [], 0
    for _, info in usable.iterrows():
        if max_events is not None and n_used >= max_events:
            break
        p = event_panel(series, info["event"], info, markets, root, lstore, every=every)
        if p is not None and len(p):
            parts.append(p)
            n_used += 1
    cuts["events_in_panel"] = n_used
    if not parts:
        return pd.DataFrame(columns=list(PANEL_COLUMNS)), cuts

    panel = pd.concat(parts, ignore_index=True)
    cuts["rows"] = len(panel)
    cuts["bracket_minutes_two_sided"] = int(
        (panel["bid"].notna() & panel["ask"].notna() & (panel["bid"] > 0) & (panel["ask"] < 100)).sum()
    )
    return panel, cuts


def staged_series(root=None, prefixes=("KXHIGH", "KXLOW")) -> list[str]:
    """Series present in the staged store, optionally filtered to the §1A universe."""
    lstore = _load_ladder_store()
    root = stores.check_staging(root)
    allser = lstore.list_series(root)
    if prefixes is None:
        return allser
    return [s for s in allser if any(s.startswith(p) for p in prefixes)]
