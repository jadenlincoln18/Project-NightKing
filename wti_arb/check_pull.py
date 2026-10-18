#!/usr/bin/env python3
"""
check_pull.py - did the pull actually work?

Log output lies. A run can print happy lines and still have stored nothing
usable, because the *_dollars parsing bug produced rows where every bid/ask
column was None. This checks the stored parquet, not the logs.

Usage:
    python3 check_pull.py                 # checks data/*
    python3 check_pull.py data/wtiw       # one store
"""
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("needs pandas + pyarrow")

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

FAIL, WARN, OK = "FAIL", "warn", "ok"


def check_store(root: Path) -> dict:
    print("=" * 74)
    print(f"STORE: {root}")
    print("=" * 74)
    res = {"root": str(root), "status": OK, "notes": []}

    cdir = root / "parquet" / "kalshi_candles"
    if not cdir.exists():
        print("  no kalshi_candles directory - nothing was written")
        res["status"] = FAIL
        return res

    files = list(cdir.rglob("*.parquet"))
    print(f"  parquet files : {len(files)}")
    if not files:
        print("  FAIL: directory exists but is empty")
        res["status"] = FAIL
        return res

    # Read files individually. Reading the directory lets Arrow infer the
    # `series=` path component as a dictionary column, which then clashes with
    # the string column of the same name stored inside each file.
    parts = []
    for f in files:
        try:
            parts.append(pd.read_parquet(f))
        except Exception as e:                                # noqa: BLE001
            print(f"    ! unreadable {f.name}: {type(e).__name__}")
    if not parts:
        print("  FAIL: no readable parquet files")
        res["status"] = FAIL
        return res
    df = pd.concat(parts, ignore_index=True)
    print(f"  rows          : {len(df):,}")
    print(f"  markets       : {df.ticker.nunique():,}")
    print(f"  events        : {df.event.nunique():,}")
    if "series" in df:
        print(f"  series        : {sorted(df.series.unique())}")

    # ---- the check that matters: are bid/ask actually populated? ----
    print("\n  --- bid/ask population (the *_dollars bug check) ---")
    bad = False
    for col in ("yes_bid_close", "yes_ask_close"):
        if col not in df.columns:
            print(f"    {col:16s} MISSING COLUMN")
            bad = True
            continue
        nn = df[col].notna().sum()
        pct = 100.0 * nn / len(df)
        flag = "" if pct > 50 else "   <== BAD"
        print(f"    {col:16s} {nn:>9,} non-null ({pct:5.1f}%){flag}")
        if pct < 5:
            bad = True
    if bad:
        print("\n    FAIL: bid/ask are empty. The *_dollars parsing fix did not")
        print("    take effect. Re-download pull_history.py and re-run.")
        res["status"] = FAIL
        res["notes"].append("bid/ask empty")
        return res

    sub = df.dropna(subset=["yes_bid_close", "yes_ask_close"])
    print(f"\n  rows with both sides quoted: {len(sub):,} "
          f"({100*len(sub)/len(df):.1f}%)")

    if len(sub):
        print("\n  --- price sanity (cents, must be 0-100) ---")
        for col in ("yes_bid_close", "yes_ask_close"):
            s = sub[col]
            oob = ((s < 0) | (s > 100)).sum()
            print(f"    {col:16s} min {s.min():6.2f}  max {s.max():6.2f}  "
                  f"mean {s.mean():6.2f}  out-of-range {oob}")
            if oob:
                res["status"] = WARN
                res["notes"].append(f"{col} out of range")

        print("\n  --- spread ---")
        sp = sub["yes_ask_close"] - sub["yes_bid_close"]
        neg = (sp < 0).sum()
        print(f"    median {sp.median():.2f}c   mean {sp.mean():.2f}c   "
              f"p90 {sp.quantile(0.9):.2f}c")
        print(f"    crossed (ask<bid): {neg:,} ({100*neg/len(sp):.2f}%)")
        if neg > 0.02 * len(sp):
            print("      WARN: >2% crossed. Stale quotes or a parsing issue.")
            res["status"] = WARN
            res["notes"].append("crossed quotes")

        print("\n  --- time coverage ---")
        print(f"    {sub.dt.min()}  ->  {sub.dt.max()}")
        span = (sub.dt.max() - sub.dt.min()).days
        print(f"    span: {span} days")
        per = sorted(df.period_min.unique())
        print(f"    period_min values: {per}")

        print("\n  --- per-market candle counts ---")
        cnt = df.groupby("ticker").size()
        print(f"    median {cnt.median():.0f}   min {cnt.min()}   "
              f"max {cnt.max()}")
        if "ladder_kind" in df:
            print(f"    ladder_kind: {df.ladder_kind.value_counts().to_dict()}")
        if "source" in df.columns:
            print(f"    source: {df.source.value_counts().to_dict()}")

        print("\n  --- sample rows ---")
        cols = [c for c in ("dt", "ticker", "bracket", "yes_bid_close",
                            "yes_ask_close", "spread", "volume")
                if c in sub.columns]
        print(sub.sort_values("dt").tail(5)[cols].to_string(index=False))

    # ---- settlement metadata: the ICE vs CME question ----
    mdir = root / "parquet" / "kalshi_market_meta"
    mfiles = list(mdir.rglob("*.parquet")) if mdir.exists() else []
    if mfiles:
        md = pd.concat([pd.read_parquet(f) for f in mfiles], ignore_index=True)
        print(f"\n  --- market meta: {len(md):,} markets ---")
        if "front_month_contract" in md:
            vc = md.front_month_contract.value_counts(dropna=False).head(12)
            print("    front_month_contract (WHICH EXCHANGE SETTLES THIS):")
            for k, v in vc.items():
                tag = ""
                ks = str(k).upper()
                if "ICE" in ks:
                    tag = "   <- ICE"
                elif any(x in ks for x in ("NYM", "CME", "CL", "COMEX")):
                    tag = "   <- CME group?"
                print(f"      {str(k)[:44]:44s} {v:6d}{tag}")
        if "expiration_value" in md:
            ev = md.expiration_value.dropna()
            print(f"\n    expiration_value present on {len(ev):,} markets "
                  f"(backtest ground truth)")
            if len(ev):
                print(f"      range {ev.min():.2f} - {ev.max():.2f}")
        if "result" in md:
            print(f"    result: {md.result.value_counts(dropna=False).to_dict()}")
        if "where" in md.columns:
            print(f"    live vs archived: "
                  f"{md['where'].value_counts().to_dict()}")
    else:
        print("\n  no kalshi_market_meta - settlement info not captured")
        res["status"] = WARN
        res["notes"].append("no meta")

    return res


def main():
    args = sys.argv[1:]
    roots = ([Path(a) for a in args] if args
             else sorted(p for p in Path("data").glob("*") if p.is_dir()))
    if not roots:
        sys.exit("no store found. Expected data/<name>/ directories.")

    out = []
    for r in roots:
        try:
            out.append(check_store(r))
        except Exception as e:                                # noqa: BLE001
            print(f"  ERROR reading {r}: {type(e).__name__}: {e}")
            out.append({"root": str(r), "status": FAIL,
                        "notes": [str(e)[:60]]})
        print()

    print("=" * 74)
    print("VERDICT")
    print("=" * 74)
    for o in out:
        note = f"  ({'; '.join(o['notes'])})" if o["notes"] else ""
        print(f"  {o['status']:5s}  {o['root']}{note}")

    if all(o["status"] == OK for o in out):
        print("\n  All stores look good. Safe to run the full pull on the Mac Mini.")
    elif any(o["status"] == FAIL for o in out):
        print("\n  Something is broken. Do NOT start the long run yet.")
    else:
        print("\n  Usable but check the warnings above.")


if __name__ == "__main__":
    main()
