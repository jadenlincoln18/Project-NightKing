"""Pull 1-minute ETH-USD candles from the Coinbase Exchange public API (keyless, free)
for the span of the hourly KXETH ladders, into waves_data/crypto/ETH-USD_1m.parquet.
Resumable (appends from the last stored minute), backoff on 429/5xx.

    python3 -m waves.pull_crypto            # ETH-USD over the KXETH span
"""
import argparse
import datetime as dt
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "waves_data" / "crypto"
API = "https://api.exchange.coinbase.com/products/%s/candles"
log = logging.getLogger("waves.crypto")


def get(product, start, end):
    q = urllib.parse.urlencode({"granularity": 60, "start": dt.datetime.fromtimestamp(start, dt.timezone.utc).isoformat(), "end": dt.datetime.fromtimestamp(end, dt.timezone.utc).isoformat()})
    req = urllib.request.Request(API % product + "?" + q, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    delay = 2
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(delay); delay = min(delay * 2, 60); continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(delay); delay = min(delay * 2, 60)
    raise RuntimeError("gave up on %s %s" % (product, start))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="ETH-USD")
    ap.add_argument("--series", default="KXETH")
    ap.add_argument("--pad-hours", type=float, default=2)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    m = pd.read_parquet(ROOT / "waves_data" / "parquet" / "kalshi_markets" / ("series=%s" % a.series) / "part.parquet", columns=["open_time_epoch", "close_time_epoch"])
    t0 = int(m.open_time_epoch.min()) - int(a.pad_hours * 3600); t1 = min(int(m.close_time_epoch.max()) + int(a.pad_hours * 3600), int(time.time()))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / ("%s_1m.parquet" % a.product)
    have = pd.read_parquet(out) if out.exists() else pd.DataFrame(columns=["ts", "low", "high", "open", "close", "volume"])
    if len(have):
        t0 = max(t0, int(have.ts.max()) + 60)
    log.info("%s: %s -> %s (%d minutes, %d requests of 300)", a.product, dt.datetime.fromtimestamp(t0, dt.timezone.utc), dt.datetime.fromtimestamp(t1, dt.timezone.utc), (t1 - t0) // 60, (t1 - t0) // 60 // 300 + 1)
    rows = []
    s = t0; n = 0
    while s < t1:
        e = min(t1, s + 300 * 60)
        d = get(a.product, s, e)
        rows.extend(d); n += 1
        s = e
        time.sleep(0.15)
        if n % 200 == 0:
            df = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"])
            pd.concat([have, df]).drop_duplicates("ts").sort_values("ts").to_parquet(out, index=False)
            log.info("%d requests, %d rows stored (to %s)", n, len(have) + len(df), dt.datetime.fromtimestamp(e, dt.timezone.utc))
    df = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"])
    allp = pd.concat([have, df]).drop_duplicates("ts").sort_values("ts")
    allp.to_parquet(out, index=False)
    log.info("done: %d rows -> %s", len(allp), out)


if __name__ == "__main__":
    main()
