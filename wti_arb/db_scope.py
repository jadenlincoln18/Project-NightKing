#!/usr/bin/env python3
"""
db_scope.py - price SCOPED Databento requests instead of the whole chain.

The naive request (LO.OPT parent, bbo-1m, 6 continuous months) came back at
$1,839. That is every strike of every expiry for every minute. The backtest
needs far less:

  - only the expiry matching each Kalshi settlement date, not all expiries
  - only the days a Kalshi market was actually live, not 190 continuous days

This prices several scoping strategies so you can pick the cheapest one that
still answers the question.

Setup:  pip install databento python-dotenv pandas pyarrow
        python3 db_scope.py
"""
import glob
import os
import sys
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import databento as db
    import pandas as pd
except ImportError:
    sys.exit("pip install databento python-dotenv pandas pyarrow")

KEY = os.environ.get("DATABENTO_API_KEY")
if not KEY:
    sys.exit("DATABENTO_API_KEY not set")
c = db.Historical(key=KEY)

GLBX = "GLBX.MDP3"
LO = "LO.OPT"          # NYMEX WTI options, parent symbology


def cost(dataset, symbols, schema, start, end, stype_in="parent"):
    try:
        return float(c.metadata.get_cost(dataset=dataset, symbols=symbols,
                                         stype_in=stype_in, schema=schema,
                                         start=start, end=end))
    except Exception as e:                                   # noqa: BLE001
        return f"ERR {type(e).__name__}: {str(e)[:60]}"


def show(label, v):
    if isinstance(v, str):
        print(f"  {label:52s} {v}")
    else:
        print(f"  {label:52s} ${v:9,.2f}")


# --------------------------------------------------------------------------
# Kalshi settlement dates from the local store
# --------------------------------------------------------------------------
print("=" * 74)
print("KALSHI SETTLEMENT DATES (from the local store)")
print("=" * 74)

dates = {}
for pat in ("data/**/kalshi_markets/**/*.parquet",
            "data/**/kalshi_market_meta/**/*.parquet"):
    for f in glob.glob(pat, recursive=True):
        try:
            df = pd.read_parquet(f)
        except Exception:                                    # noqa: BLE001
            continue
        if "series" not in df or "close_time" not in df:
            continue
        for s in ("KXWTI", "KXWTIW"):
            sub = df[df.series == s]
            if sub.empty:
                continue
            d = pd.to_datetime(sub.close_time, errors="coerce", utc=True)
            d = d[d >= "2026-03-01"].dt.date.dropna().unique()
            dates.setdefault(s, set()).update(d)

for s in sorted(dates):
    ds = sorted(dates[s])
    print(f"  {s:8s} {len(ds):4d} settlement dates  "
          f"{ds[0] if ds else '-'} to {ds[-1] if ds else '-'}")
if not dates:
    print("  none found - check the store path; falling back to estimates")

# --------------------------------------------------------------------------
print("\n" + "=" * 74)
print("STRATEGY A - whole parent chain, continuous (the $1,839 baseline)")
print("=" * 74)
show("LO.OPT bbo-1m  2026-03-01 to 2026-09-10",
     cost(GLBX, [LO], "bbo-1m", "2026-03-01", "2026-09-10"))

print("\n" + "=" * 74)
print("STRATEGY B - whole parent chain, ONE DAY (unit cost)")
print("=" * 74)
one = cost(GLBX, [LO], "bbo-1m", "2026-09-02", "2026-09-03")
show("LO.OPT bbo-1m  one trading day", one)
if not isinstance(one, str):
    for n, lab in ((26, "KXWTIW weekly, ~26 dates"),
                   (130, "KXWTI daily, ~130 dates")):
        print(f"    x{n:4d} ({lab:28s}) ${one*n:9,.2f}")

print("\n" + "=" * 74)
print("STRATEGY C - coarser schemas, whole chain, continuous")
print("=" * 74)
for schema in ("bbo-1s", "bbo-1m", "ohlcv-1m", "ohlcv-1h", "ohlcv-1d",
               "tbbo", "statistics", "definition"):
    show(f"LO.OPT {schema:11s} 2026-03-01 to 2026-09-10",
         cost(GLBX, [LO], schema, "2026-03-01", "2026-09-10"))

print("\n" + "=" * 74)
print("STRATEGY D - short windows around each settlement date")
print("=" * 74)
print("  The trade is decided in the days before settlement, so a few days")
print("  per expiry may be enough rather than the full contract life.\n")
for days in (1, 2, 5):
    v = cost(GLBX, [LO], "bbo-1m", "2026-09-01",
             (datetime(2026, 9, 1) + timedelta(days=days)).strftime("%Y-%m-%d"))
    if isinstance(v, str):
        show(f"{days}-day window", v)
        continue
    show(f"{days}-day window (one expiry cycle)", v)
    print(f"    x26 weekly expiries  ${v*26:9,.2f}")

print("\n" + "=" * 74)
print("STRATEGY E - the basis test only (no chains needed)")
print("=" * 74)
for schema in ("statistics", "ohlcv-1d"):
    show(f"LO.OPT {schema:11s} full 6 months",
         cost(GLBX, [LO], schema, "2026-03-01", "2026-09-10"))
# futures rather than options - the settlement series itself
for sym in ("CL.FUT", "CL.c.0"):
    st = "parent" if sym.endswith(".FUT") else "continuous"
    show(f"{sym:10s} statistics  full 6 months",
         cost(GLBX, [sym], "statistics", "2026-03-01", "2026-09-10", st))
    show(f"{sym:10s} ohlcv-1d    full 6 months",
         cost(GLBX, [sym], "ohlcv-1d", "2026-03-01", "2026-09-10", st))

print("""
======================================================================
READ
======================================================================
  Compare B x 26 against A. If scoping to settlement dates cuts the cost
  by an order of magnitude, that is the purchase.

  Strategy E is the ICE-vs-NYMEX basis test: it needs only the NYMEX
  settlement series, no option chains. If it is a few dollars, run it
  first - it may decide whether an ICE license is needed at all.

  Note the ICE side still returns 422 (license required). Ask Databento
  support what a personal research license for IFEU.IMPACT historical
  costs before designing around ICE data.
""")
