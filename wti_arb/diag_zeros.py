#!/usr/bin/env python3
"""
diag_zeros.py - why do some markets have 0 candles?

Two very different causes, and they need different fixes:

  NETWORK OUTAGE  -> zeros are CONTIGUOUS IN PULL ORDER (the manifest preserves
                     insertion order). Fix: re-pull with --fresh.

  DATA RETENTION  -> zeros cluster by market DATE, oldest first. Kalshi may not
                     keep 1-minute candles indefinitely. Fix: nothing to fix;
                     pull those at --period 60 instead, or accept the horizon.

Usage:  python3 diag_zeros.py
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def ticker_date(tk: str):
    """KXWTIW-25NOV07-B54.5 -> 2025-11-07 ; KXWTIW-26SEP1114-B79.50 -> 2026-09-11"""
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})", tk)
    if not m:
        return None
    yy, mon, dd = m.groups()
    try:
        return datetime(2000 + int(yy), MONTHS[mon], int(dd)).date()
    except (ValueError, KeyError):
        return None


def runs(flags):
    """Longest consecutive stretch of True, and how many stretches."""
    best = cur = nruns = 0
    prev = False
    for f in flags:
        if f:
            cur += 1
            if not prev:
                nruns += 1
            best = max(best, cur)
        else:
            cur = 0
        prev = f
    return best, nruns


for mf in sorted(Path("data").glob("*/manifest.json")):
    store = mf.parent.name
    man = json.loads(mf.read_text()).get("kalshi_candles", {})
    if not man:
        continue
    tickers = list(man.keys())                 # insertion order = pull order
    flags = [man[t].get("rows", 0) == 0 for t in tickers]
    nz = sum(flags)
    print("=" * 70)
    print(f"{store}   {len(tickers)} markets, {nz} zero ({100*nz/len(tickers):.1f}%)")
    print("=" * 70)
    if nz == 0:
        print("  clean\n")
        continue

    longest, nruns = runs(flags)
    print(f"  pull-order: {nruns} separate stretches, longest run {longest}")
    print("    (note: archived markets are pulled roughly in date order, so a")
    print("     contiguous run is consistent with BOTH causes - the date")
    print("     analysis below is what actually discriminates)")

    # by date
    zt = [t for t, f in zip(tickers, flags) if f]
    ok = [t for t, f in zip(tickers, flags) if not f]
    zd = [d for d in (ticker_date(t) for t in zt) if d]
    od = [d for d in (ticker_date(t) for t in ok) if d]
    if zd and od:
        print(f"\n  zero markets  : {min(zd)}  ->  {max(zd)}")
        print(f"  good markets  : {min(od)}  ->  {max(od)}")
        cutoff = max(zd)
        older_ok = sum(1 for d in od if d <= cutoff)
        print(f"\n  good markets dated on/before the newest zero ({cutoff}): "
              f"{older_ok}")
        if older_ok < 0.05 * len(od):
            print("    -> RETENTION: essentially every market older than this")
            print("       date has no 1-minute candles. Not a network problem.")
        else:
            print("    -> mixed: old markets both work and fail, so date alone")
            print("       does not explain it")

        # per-month breakdown
        print("\n  by month (zero / total):")
        zc = Counter((d.year, d.month) for d in zd)
        oc = Counter((d.year, d.month) for d in od)
        for k in sorted(set(zc) | set(oc)):
            z, o = zc.get(k, 0), oc.get(k, 0)
            bar = "#" * int(20 * z / max(1, z + o))
            print(f"    {k[0]}-{k[1]:02d}   {z:4d} / {z+o:4d}  {bar}")
    print()

print("=" * 70)
print("READS")
print("=" * 70)
print("""
  One long contiguous run in pull order  -> outage. Re-pull that series
      with --fresh.

  Zeros all older than a cutoff date     -> Kalshi does not retain 1-minute
      candles that far back. Re-pulling changes nothing. Either accept the
      shorter 1-minute horizon, or run those older markets at --period 60,
      which is likely retained longer.

  Note the daily series (BRENTD/GOLDD/NATGASD) only reach back ~3 months,
  while KXWTIW is WEEKLY and reaches back years. A retention limit would
  therefore hit KXWTIW hard and barely touch the others - which is exactly
  the pattern in the counts.
""")
