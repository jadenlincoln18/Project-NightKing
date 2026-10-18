"""Pull 1-minute candles for one live/recent Kalshi event into ladder/data/live_candles/
(keyless, free). Used to look at events after the store's 2026-09-10 cut-off, e.g.
the KXAAAGASDCA-26OCT04 monotonicity violation seen live.

    python3 -m ladder.pull_event KXAAAGASDCA-26OCT04
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd

from . import kapi

log = logging.getLogger("ladder.pull")
OUT = Path(__file__).resolve().parent / "data" / "live_candles"
CAP = 5000


def _blk(c, key):
    b = c.get(key) or {}
    out = {}
    for k in ("open", "high", "low", "close"):
        v = b.get(k + "_dollars", b.get(k))
        out[k] = kapi.cents(v) if isinstance(v, str) or v is None else float(v)
    return out


def candle_rows(raw, ticker):
    rows = []
    for c in raw:
        yb, ya, pr = _blk(c, "yes_bid"), _blk(c, "yes_ask"), _blk(c, "price")
        rows.append(dict(ts=int(c["end_period_ts"]), ticker=ticker,
                         volume=float(c.get("volume_fp", c.get("volume")) or 0),
                         open_interest=float(c.get("open_interest_fp", c.get("open_interest")) or 0),
                         yes_bid_open=yb["open"], yes_bid_high=yb["high"], yes_bid_low=yb["low"], yes_bid_close=yb["close"],
                         yes_ask_open=ya["open"], yes_ask_high=ya["high"], yes_ask_low=ya["low"], yes_ask_close=ya["close"],
                         price_open=pr["open"], price_high=pr["high"], price_low=pr["low"], price_close=pr["close"]))
    return rows


def pull(event, out=OUT):
    ev = kapi.get("/events/%s" % event, {"with_nested_markets": "true"})
    if not ev:
        sys.exit("event %s not found" % event)
    ev = ev.get("event") or ev
    series = ev.get("series_ticker") or event.split("-")[0]
    markets = ev.get("markets") or []
    log.info("%s: %d markets (series %s)", event, len(markets), series)
    rows, mrows = [], []
    for m in markets:
        tk = m["ticker"]
        t0 = int(pd.Timestamp(m["open_time"]).timestamp())
        t1 = min(int(pd.Timestamp(m["close_time"]).timestamp()), int(time.time()))
        got = []
        s = t0
        while s < t1:
            e = min(t1, s + CAP * 60)
            d = kapi.get("/series/%s/markets/%s/candlesticks" % (series, tk),
                         {"start_ts": s, "end_ts": e, "period_interval": 1})
            got.extend((d or {}).get("candlesticks") or [])
            s = e
        rows.extend(candle_rows(got, tk))
        mrows.append(dict(ticker=tk, event_ticker=event, series=series, strike_type=m.get("strike_type"),
                          floor_strike=m.get("floor_strike"), cap_strike=m.get("cap_strike"),
                          yes_sub_title=m.get("yes_sub_title"), volume_fp=float(m.get("volume_fp") or 0),
                          open_interest_fp=float(m.get("open_interest_fp") or 0), status=m.get("status"),
                          result=m.get("result"), open_time_epoch=t0,
                          close_time_epoch=int(pd.Timestamp(m["close_time"]).timestamp()),
                          expiration_time_epoch=int(pd.Timestamp(m["expiration_time"]).timestamp()),
                          expiration_value_num=None))
        log.info("  %s: %d candles", tk, len(got))
    d = out / ("event=%s" % event)
    d.mkdir(parents=True, exist_ok=True)
    cdf = pd.DataFrame(rows).drop_duplicates(["ticker", "ts"], keep="last").sort_values(["ticker", "ts"])
    cdf.to_parquet(d / "part.parquet", index=False)
    pd.DataFrame(mrows).to_parquet(d / "markets.parquet", index=False)
    log.info("wrote %d candles -> %s", len(cdf), d)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("events", nargs="+")
    a = ap.parse_args(argv)
    kapi.setup_logging()
    for e in a.events:
        pull(e)


if __name__ == "__main__":
    main()
