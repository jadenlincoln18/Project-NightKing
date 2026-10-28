#!/usr/bin/env python3
"""
db_probe.py - answer every open Databento question before spending anything.

All of this is free: metadata and symbology calls are not billed, and
get_cost() prices a request without executing it.

Setup:
    pip install databento python-dotenv
    echo 'DATABENTO_API_KEY=db-xxxx' >> .env
    echo '.env' >> .gitignore
    python3 db_probe.py
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass                       # fine if you exported the var instead

try:
    import databento as db
except ImportError:
    sys.exit("pip install databento python-dotenv")

KEY = os.environ.get("DATABENTO_API_KEY")
if not KEY:
    sys.exit("DATABENTO_API_KEY not set. Put it in .env or export it.")

c = db.Historical(key=KEY)

# Kalshi's WTI markets settle on ICE (custom_strike.front_month_contract =
# 'WBS 26V-ICE'). LO is the NYMEX WTI option root, the hedge we can actually
# reach through tastytrade.
TARGETS = [("IFEU.IMPACT", "WBS.OPT", "ICE WTI Bullet options"),
           ("GLBX.MDP3",   "LO.OPT",  "NYMEX WTI options")]

# The Kalshi relaunch era, where the ladder is actually tradeable.
START, END = "2026-03-01", "2026-09-10"

print("=" * 72)
print("1. DATASET RANGE  (how far back does history go?)")
print("=" * 72)
for ds, _, label in TARGETS:
    try:
        print(f"{ds:14s} {label:24s} {c.metadata.get_dataset_range(dataset=ds)}")
    except Exception as e:                                   # noqa: BLE001
        print(f"{ds:14s} ERROR {type(e).__name__}: {e}")

print("\n" + "=" * 72)
print("2. SCHEMAS  (is bbo-1m available? statistics for settlements?)")
print("=" * 72)
for ds, _, _ in TARGETS:
    try:
        s = c.metadata.list_schemas(dataset=ds)
        print(f"\n{ds}:")
        print(f"  {s}")
        for want in ("bbo-1m", "bbo-1s", "statistics", "ohlcv-1d", "definition"):
            print(f"    {want:12s} {'YES' if want in s else 'NO'}")
    except Exception as e:                                   # noqa: BLE001
        print(f"{ds}: ERROR {type(e).__name__}: {e}")

print("\n" + "=" * 72)
print("3. SYMBOLOGY  (do the option roots resolve under parent?)")
print("=" * 72)
for ds, sym, label in TARGETS:
    try:
        r = c.symbology.resolve(dataset=ds, symbols=[sym], stype_in="parent",
                                stype_out="instrument_id",
                                start_date=START, end_date="2026-03-02")
        got = r.get("result", {}).get(sym, [])
        print(f"{ds:14s} {sym:10s} -> {len(got)} mappings   ({label})")
        if r.get("not_found"):
            print(f"    NOT FOUND: {r['not_found']}")
    except Exception as e:                                   # noqa: BLE001
        print(f"{ds:14s} {sym:10s} ERROR {type(e).__name__}: {e}")

print("\n" + "=" * 72)
print(f"4. COST  ({START} to {END}, bbo-1m, whole chain)")
print("=" * 72)
total = 0.0
for ds, sym, label in TARGETS:
    try:
        cost = c.metadata.get_cost(dataset=ds, symbols=[sym], stype_in="parent",
                                   schema="bbo-1m", start=START, end=END)
        total += float(cost)
        print(f"{ds:14s} {sym:10s} ${float(cost):10,.2f}   {label}")
    except Exception as e:                                   # noqa: BLE001
        print(f"{ds:14s} {sym:10s} ERROR {type(e).__name__}: {e}")
print(f"{'TOTAL':14s} {'':10s} ${total:10,.2f}   (new accounts get $125 credit)")

print("\n" + "=" * 72)
print("5. COST of the cheap alternatives")
print("=" * 72)
for ds, sym, label in TARGETS:
    for schema in ("statistics", "ohlcv-1d", "definition"):
        try:
            cost = c.metadata.get_cost(dataset=ds, symbols=[sym],
                                       stype_in="parent", schema=schema,
                                       start=START, end=END)
            print(f"{ds:14s} {sym:8s} {schema:12s} ${float(cost):9,.2f}")
        except Exception as e:                               # noqa: BLE001
            print(f"{ds:14s} {sym:8s} {schema:12s} {type(e).__name__}")

print("""
================================================================================
READ
================================================================================
  Section 1  If IFEU starts later than 2026-03, the ICE backtest window is
             shorter than the Kalshi data allows.
  Section 2  bbo-1m must be present on BOTH. If IFEU lacks it, fall back to
             mbp-1 and resample - which costs considerably more.
  Section 3  Zero mappings means the root is wrong. Check the catalog page
             databento.com/catalog/ifeu/IFEU.IMPACT/options/WBS for the exact
             root before assuming the product is missing.
  Section 4  The number that decides the purchase.
  Section 5  'statistics' carries settlement prices. If it is cheap, the
             ICE-vs-NYMEX basis test costs almost nothing - no chains needed.

  STILL TO CHECK BY HAND, and it may make the basis test unnecessary:
  ICE WBS is the "WTI Bullet" contract. Bullet contracts are typically
  CASH-SETTLED AGAINST THE NYMEX WTI SETTLEMENT PRICE. If that holds for WBS,
  then Kalshi -> ICE -> NYMEX collapses to a single settlement number, the
  cross-exchange basis is zero by construction, and a tastytrade NYMEX hedge
  is exact. Verify on ICE's contract spec page.
""")
