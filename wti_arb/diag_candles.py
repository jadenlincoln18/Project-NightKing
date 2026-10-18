#!/usr/bin/env python3
"""
diag_candles.py - find out why the candlestick pull returned 0 rows.

Prints the raw status code and body for every variant, so we stop guessing.
Run:  python3 diag_candles.py
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

LIVE = "https://api.elections.kalshi.com/trade-api/v2"
HIST = "https://external-api.kalshi.com/trade-api/v2/historical"
UA = "Mozilla/5.0 (compatible; diag/1.0)"


def raw(url, params=None, label=""):
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    print(f"\n--- {label}")
    print(f"    {full[:150]}")
    try:
        req = urllib.request.Request(full, headers={"User-Agent": UA,
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode()
            print(f"    HTTP {r.status}   {len(body)} bytes")
            try:
                j = json.loads(body)
            except json.JSONDecodeError:
                print(f"    non-JSON: {body[:200]}")
                return None
            if isinstance(j, dict):
                print(f"    keys: {list(j.keys())}")
                for k, v in j.items():
                    if isinstance(v, list):
                        print(f"      {k}: list of {len(v)}")
                        if v:
                            print(f"        first: {json.dumps(v[0])[:220]}")
            return j
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"    HTTP {e.code} {e.reason}")
        print(f"    body: {body}")
        return None
    except Exception as e:                                   # noqa: BLE001
        print(f"    {type(e).__name__}: {e}")
        return None


print("=" * 72)
print("STEP 1  find a real WTIW market and see what fields it carries")
print("=" * 72)

ev = raw(f"{LIVE}/events",
         {"series_ticker": "KXWTIW", "status": "open",
          "with_nested_markets": "true", "limit": 2},
         "events (nested)")

ticker = series = None
if ev and ev.get("events"):
    e0 = ev["events"][0]
    print(f"\n    event keys: {list(e0.keys())}")
    mkts = e0.get("markets") or []
    print(f"    nested markets: {len(mkts)}")
    if mkts:
        m = mkts[0]
        ticker = m.get("ticker")
        print(f"\n    FIRST MARKET FIELDS:")
        for k in sorted(m.keys()):
            v = m[k]
            if not isinstance(v, (dict, list)):
                print(f"      {k:26s} = {v}")
        # the two fields the puller needs for the time window
        print(f"\n    open_time  present? {'open_time' in m}  -> {m.get('open_time')}")
        print(f"    close_time present? {'close_time' in m} -> {m.get('close_time')}")

if not ticker:
    print("\n!! could not get a ticker; stopping")
    sys.exit(1)

series = "KXWTIW"
now = int(time.time())
wide0, wide1 = now - 30 * 86400, now

print("\n" + "=" * 72)
print(f"STEP 2  candlestick endpoint variants for {ticker}")
print("=" * 72)

# a) the URL the puller uses
raw(f"{LIVE}/series/{series}/markets/{ticker}/candlesticks",
    {"start_ts": wide0, "end_ts": wide1, "period_interval": 1},
    "A: live /series/{s}/markets/{t}/candlesticks  period=1")

# b) same, hourly - maybe 1-min is restricted
raw(f"{LIVE}/series/{series}/markets/{ticker}/candlesticks",
    {"start_ts": wide0, "end_ts": wide1, "period_interval": 60},
    "B: same but period=60")

# c) no time params at all
raw(f"{LIVE}/series/{series}/markets/{ticker}/candlesticks",
    {"period_interval": 60},
    "C: no start/end")

# d) archived host
raw(f"{HIST}/markets/{ticker}/candlesticks",
    {"start_ts": wide0, "end_ts": wide1, "period_interval": 60},
    "D: historical host")

# e) url-encoded ticker (it contains a '.')
raw(f"{LIVE}/series/{series}/markets/{urllib.parse.quote(ticker)}/candlesticks",
    {"start_ts": wide0, "end_ts": wide1, "period_interval": 60},
    "E: percent-encoded ticker")

# f) bulk endpoint
raw(f"{LIVE}/markets/candlesticks",
    {"tickers": ticker, "start_ts": wide0, "end_ts": wide1,
     "period_interval": 60},
    "F: bulk /markets/candlesticks")

# g) does the market itself resolve?
raw(f"{LIVE}/markets/{ticker}", None, "G: single market lookup")

print("\n" + "=" * 72)
print("STEP 3  an ARCHIVED (settled) market")
print("=" * 72)
hm = raw(f"{HIST}/markets", {"series_ticker": "KXWTIW", "limit": 3},
         "historical markets list")
if hm and hm.get("markets"):
    a = hm["markets"][0]
    at = a.get("ticker")
    print(f"\n    archived ticker: {at}")
    for k in sorted(a.keys()):
        if not isinstance(a[k], (dict, list)):
            print(f"      {k:26s} = {a[k]}")
    if at:
        raw(f"{HIST}/markets/{at}/candlesticks",
            {"start_ts": now - 400 * 86400, "end_ts": now,
             "period_interval": 60},
            "H: archived candlesticks, 400d window")
        raw(f"{HIST}/markets/{at}/candlesticks",
            {"period_interval": 60},
            "I: archived candlesticks, no window")

print("\n" + "=" * 72)
print("READ THIS")
print("=" * 72)
print("""
Look for the first variant that returned a non-empty list.

  401 everywhere      -> candlesticks need auth (orderbook does not).
                         You would need a Kalshi API key for this endpoint.
  404 on A but D ok   -> live markets do not serve candles; use historical.
  200 but empty list  -> the time window is wrong, not the URL.
  G shows open_time   -> the puller can compute a correct window.
  G lacks open_time   -> nested markets omit it, the puller fell back to a
                         400-day window, and older markets fell outside it.
""")