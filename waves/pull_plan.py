"""Choose what to pull into waves_data from the discovery tables, and estimate it.

    python3 -m waves.pull_plan                 # writes waves_data/pull_series.txt (+ _commodity.txt), prints the plan

Selection (brief section 3: breadth across market types over depth on any one):
  - numeric ladders only (>= 3 strike markets in the event); the event's own category
  - every non-Commodities series with at least one ladder event, ordered so that the
    categories are interleaved (round-robin by category, most ladder-events first within
    a category) - a partial pull is still broad
  - the Commodities series already in ../data are listed separately for the forward
    extension (`--since 2026-09-01`); Commodities series NOT in the store go in the main list
Estimated requests = one per 5,000 minutes of each market's life, plus one per event page.
"""
import argparse
import json
import math
import time
from pathlib import Path

import pandas as pd

from ladder.store import list_series

ROOT = Path(__file__).resolve().parent.parent
DISC = ROOT / "waves_data" / "discovery"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-events", type=int, default=1)
    ap.add_argument("--min-volume", type=float, default=1.0, help="markets with lifetime volume below this are not pulled (no trades usually means no quotes)")
    ap.add_argument("--cap", type=float, default=40000, help="request cap per category (series taken in events-desc order until the cap)")
    ap.add_argument("--cap-financial", type=float, default=20000, help="cap for Crypto / Financials / Sports / Elections, which have an underlying or are enormous")
    ap.add_argument("--exclude-cats", default="Sports,Financials,Crypto", help="categories left out of the main list (have an underlying; already sampled; their daily ladders have 5-20k archived markets each)")
    ap.add_argument("--cheap-first", action="store_true", default=True, help="order the list by estimated requests ascending so breadth lands first")
    ap.add_argument("--min-life-days", type=float, default=0.5, help="drop series whose median market life is shorter (hourly / 15-minute ladders: the live listing shows a fraction of their archived markets, so the estimate is wrong by ~8x and one series takes a day)")
    a = ap.parse_args(argv)
    ev = pd.read_parquet(DISC / "events.parquet"); mk = pd.read_parquet(DISC / "markets.parquet")
    lad = ev[ev.is_ladder]
    m = mk[mk.event_ticker.isin(lad.event_ticker)].copy()
    m = m[m.volume >= a.min_volume]
    now = time.time()
    end = m.close_epoch.where(m.close_epoch < now, now)
    m["life_min"] = ((end - m.open_epoch).clip(lower=0) / 60.0).fillna(0)
    m["requests"] = (m.life_min / 5000.0).apply(math.ceil).clip(lower=1)
    in_store = set(list_series())
    g = m.groupby(["category", "series"]).agg(events=("event_ticker", "nunique"), markets=("ticker", "size"), requests=("requests", "sum"), volume=("volume", "sum"), life_days=("life_min", lambda x: x.median() / 1440)).reset_index()
    g = g[g.events >= a.min_events]
    subdaily = g[g.life_days < a.min_life_days]
    print("sub-daily series dropped (median life < %.1f d): %d (%s)" % (a.min_life_days, len(subdaily), ", ".join(subdaily.sort_values("markets", ascending=False).series.head(15))))
    g = g[g.life_days >= a.min_life_days]
    comm_ext = g[(g.category == "Commodities") & g.series.isin(in_store)]
    excl = {c.strip() for c in a.exclude_cats.split(",") if c.strip()}
    main_ = g[~g.series.isin(in_store) & ~g.category.isin(excl)].copy()
    print("excluded categories: %s (%d series)" % (", ".join(sorted(excl)), int(g[~g.series.isin(in_store) & g.category.isin(excl)].shape[0])))
    # per-category request caps: most ladder-events first within a category until the cap
    main_ = main_.sort_values(["category", "events"], ascending=[True, False])
    keep = []
    used = {}
    for _, r in main_.iterrows():
        cap = a.cap_financial if r.category in ("Crypto", "Financials", "Sports", "Elections") else a.cap
        if used.get(r.category, 0) + r.requests <= cap:   # greedy: skip a series that does not fit, keep trying smaller ones
            used[r.category] = used.get(r.category, 0) + r.requests; keep.append(True)
        else:
            keep.append(False)
    keep = pd.Series(keep, index=main_.index)
    dropped = main_[~keep]
    main_ = main_[keep].copy()
    print("capped out: %d series, %s requests (%s)" % (len(dropped), "{:,}".format(int(dropped.requests.sum())), ", ".join("%s %d" % (c, n) for c, n in dropped.groupby("category").size().items())))
    # round-robin by category so a partial pull is still broad
    main_["rank_in_cat"] = main_.groupby("category").cumcount()
    if a.cheap_first:
        main_ = main_.sort_values("requests")
    else:
        main_ = main_.sort_values(["rank_in_cat", "events"], ascending=[True, False])
    (ROOT / "waves_data" / "pull_series.txt").write_text("\n".join(main_.series) + "\n")
    (ROOT / "waves_data" / "pull_series_commodity.txt").write_text("\n".join(comm_ext.series) + "\n")
    (ROOT / "waves_data" / "pull_plan.json").write_text(json.dumps(dict(min_volume=a.min_volume, cap=a.cap, cap_financial=a.cap_financial, series=len(main_), events=int(main_.events.sum()), markets=int(main_.markets.sum()), requests=int(main_.requests.sum()))))
    print("MAIN PULL: %d series, %s ladder events, %s markets, ~%s candle requests (%.1f h at 3 rps)" % (len(main_), "{:,}".format(int(main_.events.sum())), "{:,}".format(int(main_.markets.sum())), "{:,}".format(int(main_.requests.sum())), main_.requests.sum() / 3 / 3600))
    print(main_.groupby("category").agg(series=("series", "size"), events=("events", "sum"), markets=("markets", "sum"), requests=("requests", "sum")).sort_values("requests", ascending=False).to_string())
    print("\nCOMMODITY EXTENSION (--since 2026-09-01): %d series already in the store" % len(comm_ext))
    print("\nfirst 40 in pull order:", ", ".join(main_.series.head(40)))
    return main_


if __name__ == "__main__":
    main()
