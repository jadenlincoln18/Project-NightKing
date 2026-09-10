#!/usr/bin/env python3
"""
findings.py - write FINDINGS.md from the store: per series, the usable date
window, event and market counts, settlement source, ladder type, total
candles, and a month-by-month coverage table. Then series grouped by
settlement source and a Databento-purchase shortlist.

Reads the manifest (per-market fetch outcome), the markets/events tables and
probe.json (series titles). Does not read candle parquet - the manifest already
carries rows per market - so it is cheap to re-run:
    python3 findings.py --out data
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import kalshi_common as kc
from kalshi_common import Store, fmt_int

HEDGEABLE_HINTS = ("ICE", "CME", "NYMEX", "COMEX", "CBOT", "CBOE")
USABLE_SHARE = 0.5      # a month is "live" when >= 50% of its markets have candles
MIN_USABLE_MONTHS = 2


def month_of_epoch(ts: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m")
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def series_titles(root: Path) -> Dict[str, dict]:
    p = root / "probe.json"
    if not p.exists():
        return {}
    try:
        probe = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}
    out = {}
    for s in (probe.get("series") or {}).get("selected") or []:
        out[s["ticker"]] = s
    return out


def build(store: Store) -> Dict[str, Any]:
    markets = store.read_all("kalshi_markets")
    events = store.read_all("kalshi_events")
    titles = series_titles(store.root)
    entries = list(store.entries.values())
    periods = sorted({e.get("period") for e in entries if e.get("period") is not None})
    period = periods[0] if periods else None
    if len(periods) > 1:
        period = max(periods, key=lambda p: sum(1 for e in entries if e.get("period") == p))
    ents = [e for e in entries if e.get("period") == period]

    by_series: Dict[str, Dict[str, Any]] = {}
    ser_names = set(e.get("series") for e in ents)
    if markets is not None and not markets.empty:
        ser_names |= set(markets["series"].dropna().unique())
    for s in sorted(x for x in ser_names if x):
        rec: Dict[str, Any] = {"series": s, "title": (titles.get(s) or {}).get("title"),
                               "category": (titles.get(s) or {}).get("category"),
                               "cadence": (titles.get(s) or {}).get("cadence"),
                               "group": (titles.get(s) or {}).get("group")}
        mk = markets[markets["series"] == s] if markets is not None and not markets.empty else None
        ev = events[events["series"] == s] if events is not None and not events.empty else None
        rec["n_events"] = int(len(ev)) if ev is not None else None
        rec["n_markets"] = int(len(mk)) if mk is not None else None
        if mk is not None and len(mk):
            rec["settlement_sources"] = dict(Counter(mk["settlement_source_name"].dropna()).most_common(4))
            kinds = Counter(mk["ladder_kind"].dropna())
            rec["ladder_kind"] = kinds.most_common(1)[0][0] if kinds else None
            rec["ladder_kinds"] = dict(kinds)
            rec["me_missing_share"] = float(mk["mutually_exclusive"].isna().mean())
            settled = mk[mk["status"].isin(["settled", "finalized"])]
            rec["n_settled"] = int(len(settled))
            has_val = settled[settled["expiration_value"].map(lambda v: not kc.is_empty(v))] if len(settled) else settled
            rec["settled_with_value"] = int(len(has_val))
            months = has_val["close_time"].dropna().map(lambda v: str(v)[:7]) if len(has_val) else []
            rec["expiration_value_window"] = (min(months), max(months)) if len(months) else None
            fm = mk["custom_strike.front_month_contract"].dropna() if "custom_strike.front_month_contract" in mk.columns else []
            rec["front_month_contracts"] = dict(Counter(fm).most_common(3))
            rec["ticker_formats"] = dict(Counter(mk["ticker_format"]))
        else:
            rec.update({"settlement_sources": {}, "ladder_kind": None, "ladder_kinds": {},
                        "me_missing_share": None, "n_settled": None, "settled_with_value": None,
                        "expiration_value_window": None,
                        "front_month_contracts": {}, "ticker_formats": {}})
        se = [e for e in ents if e.get("series") == s]
        c = Counter(e.get("status") for e in se)
        rec["attempted"] = len(se)
        rec["ok"], rec["empty"], rec["not_found"], rec["error"] = (c.get("ok", 0), c.get("empty", 0),
                                                                   c.get("not_found", 0), c.get("error", 0))
        rec["candles"] = int(sum(int(e.get("rows") or 0) for e in se))
        months: Dict[str, Dict[str, int]] = defaultdict(lambda: {"markets": 0, "with_candles": 0, "candles": 0})
        t0s, t1s = [], []
        for e in se:
            m = month_of_epoch(e.get("t1")) or month_of_epoch(e.get("t0"))
            if not m:
                continue
            months[m]["markets"] += 1
            if e.get("status") == "ok":
                months[m]["with_candles"] += 1
                months[m]["candles"] += int(e.get("rows") or 0)
                t0s.append(e.get("t0"))
                t1s.append(e.get("t1"))
        rec["months"] = dict(sorted(months.items()))
        rec["first_candle"] = kc.epoch_to_iso(min(t0s))[:10] if t0s else None
        rec["last_candle"] = kc.epoch_to_iso(max(t1s))[:10] if t1s else None
        live_months = [m for m, v in rec["months"].items()
                       if v["markets"] and v["with_candles"] / v["markets"] >= USABLE_SHARE]
        rec["usable_from"] = live_months[0] if live_months else None
        rec["usable_to"] = live_months[-1] if live_months else None
        rec["usable_months"] = len(live_months)
        rec["hedgeable_source"] = any(h in (src or "").upper() for src in rec["settlement_sources"]
                                      for h in HEDGEABLE_HINTS)
        by_series[s] = rec
    return {"period": period, "series": by_series, "counts": store.counts(period)}


def render(f: Dict[str, Any], root: Path) -> str:
    L: List[str] = []
    L.append("# FINDINGS - Kalshi commodity ladder history")
    L.append("")
    L.append("Generated %s from `%s` (period = %s min). Numbers come from the manifest and the "
             "markets/events tables, not from logs." % (kc.now_iso(), root, f["period"]))
    c = f["counts"]
    L.append("")
    L.append("Manifest: ok=%d empty=%d not_found=%d error=%d, candles=%s." %
             (c.get("ok", 0), c.get("empty", 0), c.get("not_found", 0), c.get("error", 0), fmt_int(c.get("rows", 0))))
    if c.get("error"):
        L.append("")
        L.append("**%d markets ended in `error` - re-run collect.py (resume retries them) before "
                 "trusting the activity numbers below.**" % c["error"])
    L.append("")
    L.append("## Per series")
    L.append("")
    L.append("| series | title | settles on | ladder | events | markets | w/ candles | candles | usable window | months |")
    L.append("|---|---|---|---|---:|---:|---:|---:|---|---:|")
    for s, r in sorted(f["series"].items(), key=lambda kv: -(kv[1]["candles"] or 0)):
        src = ", ".join(r["settlement_sources"].keys()) or "-"
        win = ("%s .. %s" % (r["usable_from"], r["usable_to"])) if r["usable_from"] else "none"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            s, (r["title"] or "")[:40], src[:40], r["ladder_kind"] or "?",
            r["n_events"] if r["n_events"] is not None else "?",
            r["n_markets"] if r["n_markets"] is not None else "?",
            r["ok"], fmt_int(r["candles"]), win, r["usable_months"]))
    L.append("")
    L.append("`usable window` = first through last month in which at least %d%% of that month's "
             "markets returned candles. Markets before the window existed but did not trade." % int(100 * USABLE_SHARE))

    L.append("")
    L.append("## Series by settlement source")
    L.append("")
    groups: Dict[str, List[str]] = defaultdict(list)
    for s, r in f["series"].items():
        if r["settlement_sources"]:
            for src in r["settlement_sources"]:
                groups[src].append(s)
        else:
            groups["(none recorded)"].append(s)
    for src, ss in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        tag = " (exchange-settled: CME/ICE option is a candidate hedge)" if any(
            h in (src or "").upper() for h in HEDGEABLE_HINTS) else ""
        L.append("- **%s**%s: %s" % (src, tag, ", ".join(sorted(ss))))

    L.append("")
    L.append("## Databento shortlist")
    L.append("")
    short = [(s, r) for s, r in f["series"].items()
             if r["hedgeable_source"] and r["usable_months"] >= MIN_USABLE_MONTHS]
    if short:
        L.append("Series settling on an exchange source with a usable window of at least %d months:" % MIN_USABLE_MONTHS)
        L.append("")
        for s, r in sorted(short, key=lambda kv: -(kv[1]["candles"] or 0)):
            L.append("- **%s** %s .. %s (%d months, %s candles); front-month contracts seen: %s" % (
                s, r["usable_from"], r["usable_to"], r["usable_months"], fmt_int(r["candles"]),
                ", ".join("%s (%d)" % kv for kv in r["front_month_contracts"].items()) or "-"))
        L.append("")
        L.append("Buy CME options history covering those windows (plus a month either side for the "
                 "density fit warm-up). Everything else settles on an aggregated index or has no "
                 "usable window yet.")
    else:
        L.append("No series meets both criteria yet (exchange settlement source AND >= %d usable months)." % MIN_USABLE_MONTHS)

    L.append("")
    L.append("## Month-by-month coverage")
    for s, r in sorted(f["series"].items(), key=lambda kv: -(kv[1]["candles"] or 0)):
        if not r["months"]:
            continue
        L.append("")
        L.append("### %s%s" % (s, (" - " + r["title"]) if r["title"] else ""))
        L.append("")
        det = []
        if r["cadence"]:
            det.append("cadence %s" % r["cadence"])
        if r["ladder_kinds"]:
            det.append("ladder %s" % json.dumps(r["ladder_kinds"]))
        if r["n_settled"] is not None:
            win = r.get("expiration_value_window")
            det.append("settled %d, with expiration_value %d%s" % (
                r["n_settled"], r["settled_with_value"],
                (" (markets closing %s .. %s)" % win) if win else ""))
        if r["ticker_formats"]:
            det.append("ticker formats %s" % json.dumps(r["ticker_formats"]))
        if r["error"]:
            det.append("**errors %d**" % r["error"])
        if r["not_found"]:
            det.append("404 on both hosts %d" % r["not_found"])
        L.append("; ".join(det))
        L.append("")
        L.append("| month | markets | zero-candle | %% live | candles |")
        L.append("|---|---:|---:|---:|---:|")
        for m, v in r["months"].items():
            zero = v["markets"] - v["with_candles"]
            live = 100.0 * v["with_candles"] / v["markets"] if v["markets"] else 0.0
            L.append("| %s | %d | %d | %.0f%% | %s |" % (m, v["markets"], zero, live, fmt_int(v["candles"])))
    L.append("")
    return "\n".join(L)


def write_findings(store: Store, path: Optional[Path] = None) -> Path:
    path = Path(path) if path else store.root / "FINDINGS.md"
    f = build(store)
    kc.atomic_write_text(path, render(f, store.root))
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data")
    a = ap.parse_args(argv)
    p = write_findings(Store(Path(a.out)))
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
