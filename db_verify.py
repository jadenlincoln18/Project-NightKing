#!/usr/bin/env python3
"""
db_verify.py - validate the Databento store (data_cme/). Reads parquet and the
manifest, never logs. Column population, not row counts. Exit 1 on FAIL.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import db_common as dc


class Rep:
    def __init__(self) -> None:
        self.fails = 0
        self.warns = 0

    def ok(self, c, d=""):
        print("PASS %-36s %s" % (c, d))

    def warn(self, c, d=""):
        self.warns += 1
        print("WARN %-36s %s" % (c, d))

    def fail(self, c, d=""):
        self.fails += 1
        print("FAIL %-36s %s" % (c, d))


def run(root: Path, strict: bool = False) -> int:
    import pandas as pd
    root = Path(root)
    print("=" * 78)
    print("DB VERIFY %s" % root)
    print("=" * 78)
    rep = Rep()
    man = dc.Manifest(root / "manifest.jsonl")
    if not man.entries:
        rep.fail("manifest", "no entries (nothing bought yet?)")
        return 1
    spent = man.spent()
    rep.ok("manifest", "%d requests, $%.2f spent" % (len(man.entries), spent))
    missing = [e["name"] for e in man.entries.values() if e.get("status") == "ok" and not Path(e.get("parquet_path", "")).exists()]
    if missing:
        rep.fail("manifest: parquet present", "missing: %s" % missing[:5])
    else:
        rep.ok("manifest: parquet present")
    raw_missing = [e["name"] for e in man.entries.values() if e.get("status") == "ok" and not Path(e.get("raw_path", "")).exists()]
    if raw_missing:
        rep.warn("manifest: raw DBN present", "missing: %s" % raw_missing[:5])
    else:
        rep.ok("manifest: raw DBN present")

    defs = dc.read_all(root / "parquet" / "options_definition")
    if defs is None:
        rep.warn("definitions", "none on disk")
    else:
        symcol = "raw_symbol" if "raw_symbol" in defs.columns else "symbol"
        parsed = defs[symcol].map(dc.parse_option_symbol)
        n_opt = int(parsed.notna().sum())
        exp = pd.to_datetime(defs["expiration"], utc=True, errors="coerce")
        if n_opt == 0:
            rep.fail("definitions: option symbols parse", "0 of %d parse as options" % len(defs))
        else:
            rep.ok("definitions: option symbols parse", "%d options, %d other (spreads)" % (n_opt, len(defs) - n_opt))
        if exp[parsed.notna()].isna().any():
            rep.fail("definitions: expiration populated", "%d option rows without expiration" % int(exp[parsed.notna()].isna().sum()))
        else:
            rep.ok("definitions: expiration populated")
        sp = pd.to_numeric(defs.get("strike_price"), errors="coerce") if "strike_price" in defs.columns else None
        if sp is not None:
            bad = int(((sp <= 0) | sp.isna())[parsed.notna()].sum())
            (rep.fail if bad else rep.ok)("definitions: strike_price > 0", "%d bad" % bad if bad else "")

    tb = dc.read_all(root / "parquet" / "options_tbbo")
    if tb is None:
        rep.warn("tbbo", "none on disk")
    else:
        for col in ("bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00", "ts_event", "symbol"):
            if col not in tb.columns:
                rep.fail("tbbo: columns", "missing %s" % col)
        if {"bid_px_00", "ask_px_00"} <= set(tb.columns):
            # per FILE: one root stored with an all-null side is the silent failure
            dead = []
            for f in sorted((root / "parquet" / "options_tbbo").rglob("part.parquet")):
                d = pd.read_parquet(f, columns=["bid_px_00", "ask_px_00"])
                if len(d) and (d["bid_px_00"].isna().all() or d["ask_px_00"].isna().all()):
                    dead.append(f.parent.name)
            nb = float(tb["bid_px_00"].isna().mean())
            na = float(tb["ask_px_00"].isna().mean())
            if dead:
                rep.fail("tbbo: bid/ask populated", "an entire side is null in %s" % dead[:4])
            elif max(nb, na) > 0.05:
                rep.warn("tbbo: bid/ask populated", "null share bid %.1f%% ask %.1f%% (one-sided books are real in the wings)" % (100 * nb, 100 * na))
            else:
                rep.ok("tbbo: bid/ask populated", "null share bid %.2f%% ask %.2f%%" % (100 * nb, 100 * na))
            both = tb["bid_px_00"].notna() & tb["ask_px_00"].notna()
            crossed = int((tb.loc[both, "ask_px_00"] < tb.loc[both, "bid_px_00"]).sum())
            share = crossed / max(1, int(both.sum()))
            (rep.fail if share > 0.001 else rep.ok)("tbbo: ask >= bid", "%d crossed (%.4f%%)" % (crossed, 100 * share))
            px = pd.concat([tb["bid_px_00"], tb["ask_px_00"]]).dropna()
            bad = int(((px < 0) | (px > 500)).sum())
            (rep.fail if bad else rep.ok)("tbbo: prices sane (0..500 $/bbl)", "%d outside" % bad if bad else "")
        if defs is not None and "symbol" in tb.columns:
            symcol = "raw_symbol" if "raw_symbol" in defs.columns else "symbol"
            known = set(defs[symcol])
            unknown = sorted(set(tb["symbol"]) - known)
            (rep.fail if unknown else rep.ok)("tbbo: symbols map to definitions",
                                              "%d unknown e.g. %s" % (len(unknown), unknown[:3]) if unknown else "%d symbols" % tb["symbol"].nunique())
        rep.ok("tbbo: rows", "{:,}".format(len(tb)))

    fs = dc.read_all(root / "parquet" / "futures_stats")
    if fs is None:
        rep.warn("futures_stats", "none on disk")
    else:
        st = fs[fs["stat_type"] == dc.STAT_SETTLEMENT] if "stat_type" in fs.columns else fs.iloc[0:0]
        if st.empty:
            rep.fail("futures_stats: settlement records", "no stat_type=%d rows; types: %s" % (dc.STAT_SETTLEMENT, sorted(fs["stat_type"].unique().tolist()) if "stat_type" in fs.columns else "?"))
        else:
            px = pd.to_numeric(st["price"], errors="coerce")
            bad = int(((px <= 0) | (px > 500) | px.isna()).sum())
            (rep.fail if bad else rep.ok)("futures_stats: settlement prices sane", "%d settlement rows" % len(st) if not bad else "%d bad" % bad)
    b = root / "parquet" / "basis" / "part.parquet"
    if b.exists():
        bj = pd.read_parquet(b)
        have = bj[bj["expiration_value"].notna()]
        j = int(have["nymex_fm"].notna().sum()) + 0
        jc = int(have["nymex_c0"].notna().sum())
        if jc == 0:
            rep.fail("basis: joined", "no Kalshi date joined to a NYMEX settlement")
        else:
            rep.ok("basis: joined", "%d of %d Kalshi events joined (c.0), %d to the named front month" % (jc, len(have), j))
    print("\n%s  (%d FAIL, %d WARN)" % ("FAIL" if rep.fails or (strict and rep.warns) else "PASS", rep.fails, rep.warns))
    return 1 if rep.fails or (strict and rep.warns) else 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(dc.DEFAULT_OUT))
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    return run(Path(a.out), a.strict)


if __name__ == "__main__":
    sys.exit(main())
