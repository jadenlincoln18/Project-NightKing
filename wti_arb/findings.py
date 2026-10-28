#!/usr/bin/env python3
"""
findings.py - write FINDINGS.md from the store: per series, the usable date
window, event and market counts, settlement source, ladder type, total
candles, and a month-by-month coverage table. Then series grouped by
settlement source and a Databento-purchase shortlist.

Reads the manifest (per-market fetch outcome), the markets/events tables and
probe.json (series titles). Without --tails it does not read candle parquet - the
manifest already carries rows per market - so it is cheap to re-run:
    python3 findings.py --out data
    python3 findings.py --out data --tails   # + bracket depth by price band (reads candles)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import kalshi_common as kc
from kalshi_common import Store, fmt_int

import re

HEDGEABLE_HINTS = ("ICE", "CME", "NYMEX", "COMEX", "CBOT", "CBOE")
USABLE_SHARE = 0.5          # a month is "live" when >= 50% of its markets have candles ...
MIN_CANDLES_PER_MARKET = 50  # ... AND the month averages at least this many candles per market
MIN_MEDIAN_VOLUME = 100      # "tradeable": median lifetime volume per bracket, in contracts
MIN_USABLE_MONTHS = 2
TAIL_BANDS = (("deep tail", 0.0, 5.0), ("moderate tail", 5.0, 20.0), ("near the money", 20.0, 80.0),
              ("deep in the money", 80.0, 100.01))
UNIT_CONTRACTS = 500         # the standard hedged unit the brief sizes against


def is_exchange_source(name: Any) -> bool:
    """Whole-word match: 'ICE' must not match 'Office' or 'Price'."""
    if not isinstance(name, str):
        return False
    return any(re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % h, name) for h in HEDGEABLE_HINTS)


def month_segments(months: List[str]) -> List[Tuple[str, str]]:
    """Contiguous runs of YYYY-MM strings -> [(first, last), ...]."""
    out: List[Tuple[str, str]] = []
    for m in sorted(months):
        y, mo = int(m[:4]), int(m[5:7])
        if out:
            ly, lmo = int(out[-1][1][:4]), int(out[-1][1][5:7])
            nxt = (ly + (lmo // 12), (lmo % 12) + 1)
            if (y, mo) == nxt:
                out[-1] = (out[-1][0], m)
                continue
        out.append((m, m))
    return out


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
        if mk is not None and len(mk) and "volume_fp" in mk.columns:
            cm = mk["close_time"].map(lambda v: str(v)[:7] if not kc.is_empty(v) else None)
            vol = mk["volume_fp"].fillna(0.0)
            for m, sub in vol.groupby(cm):
                if m and m in months:
                    months[m]["vol_median"] = float(sub.median())
                    months[m]["vol_p90"] = float(sub.quantile(0.9))
                    months[m]["vol_zero_share"] = float((sub == 0).mean())
        rec["months"] = dict(sorted(months.items()))
        rec["first_candle"] = kc.epoch_to_iso(min(t0s))[:10] if t0s else None
        rec["last_candle"] = kc.epoch_to_iso(max(t1s))[:10] if t1s else None
        live_months = [m for m, v in rec["months"].items()
                       if v["markets"] and v["with_candles"] / v["markets"] >= USABLE_SHARE
                       and v["candles"] / v["markets"] >= MIN_CANDLES_PER_MARKET]
        rec["usable_segments"] = month_segments(live_months)
        rec["usable_from"] = live_months[0] if live_months else None
        rec["usable_to"] = live_months[-1] if live_months else None
        rec["usable_months"] = len(live_months)
        # candle density is quoting, not depth: a TRADEABLE month also needs real volume
        tradeable = [m for m in live_months
                     if (rec["months"][m].get("vol_median") or 0.0) >= MIN_MEDIAN_VOLUME]
        rec["tradeable_segments"] = month_segments(tradeable)
        rec["tradeable_months"] = len(tradeable)
        # hedgeable only when the DOMINANT settlement source is an exchange
        top = next(iter(rec["settlement_sources"]), None)
        rec["dominant_source"] = top
        rec["hedgeable_source"] = is_exchange_source(top)
        by_series[s] = rec
    return {"period": period, "series": by_series, "counts": store.counts(period)}


def tail_depth(store: Store, f: Dict[str, Any], period: Optional[int] = None) -> Dict[str, Any]:
    """For every shortlisted series: brackets classified by their MEDIAN mid over
    the tradeable months, with lifetime volume (markets table) and median spread
    (candles). This is the number the purchase turns on: is the ladder liquid
    where the strategy trades (5-20c), or only at the money?"""
    import pandas as pd
    period = period or f.get("period") or 1
    markets = store.read_all("kalshi_markets")
    vol = (markets.set_index("ticker")["volume_fp"] if markets is not None and not markets.empty
           else pd.Series(dtype="float64"))
    out: Dict[str, Any] = {}
    for s, r in f["series"].items():
        if not (r.get("hedgeable_source") and r.get("tradeable_months", 0) >= MIN_USABLE_MONTHS):
            continue
        all_months = {m for seg in r["tradeable_segments"] for m in r["months"] if seg[0] <= m <= seg[1]}
        base = store.pq / "kalshi_candles" / ("period=%d" % period) / ("series=%s" % s)
        files = sorted(base.rglob("part.parquet")) if base.exists() else []
        if not files:
            continue
        frames = []
        for p in files:
            d = pd.read_parquet(p, columns=["ticker", "dt", "yes_bid_close", "yes_ask_close"])
            d["month"] = d["dt"].dt.strftime("%Y-%m")
            d = d[d["month"].isin(all_months)]
            if len(d):
                frames.append(d)
        if not frames:
            continue
        c = pd.concat(frames, ignore_index=True)
        c["mid"] = (c["yes_bid_close"] + c["yes_ask_close"]) / 2.0
        c["spread"] = c["yes_ask_close"] - c["yes_bid_close"]
        segments = []
        # one table per contiguous tradeable segment: the eras must not be pooled
        for seg in r["tradeable_segments"]:
            cs = c[(c["month"] >= seg[0]) & (c["month"] <= seg[1])]
            if not len(cs):
                continue
            per = cs.groupby("ticker").agg(med_mid=("mid", "median"), med_spread=("spread", "median"),
                                           candles=("mid", "size")).reset_index()
            per["life_vol"] = per["ticker"].map(vol).fillna(0.0)
            bands = []
            for name, lo, hi in TAIL_BANDS:
                g = per[(per["med_mid"] >= lo) & (per["med_mid"] < hi)]
                if not len(g):
                    bands.append({"band": name, "lo": lo, "hi": hi, "brackets": 0})
                    continue
                q = g["life_vol"].quantile
                bands.append({"band": name, "lo": lo, "hi": hi, "brackets": int(len(g)),
                              "vol_p25": float(q(0.25)), "vol_median": float(q(0.5)),
                              "vol_p90": float(q(0.9)),
                              "share_under_unit": float((g["life_vol"] < UNIT_CONTRACTS).mean()),
                              "spread_median": float(g["med_spread"].median()),
                              "spread_p75": float(g["med_spread"].quantile(0.75))})
            segments.append({"from": seg[0], "to": seg[1], "brackets": int(len(per)), "bands": bands})
        if segments:
            out[s] = {"segments": segments}
    return out


def render_tails(t: Dict[str, Any]) -> List[str]:
    L: List[str] = ["", "## Tail depth on the shortlist (--tails)", ""]
    if not t:
        L.append("No shortlisted series with candles in tradeable months.")
        return L
    L.append("Brackets are classified by their median mid over the tradeable months. Lifetime volume "
             "is contracts traded over the bracket's life (markets table); spread is the median "
             "close-to-close spread (candles). `< unit` = share of brackets with lifetime volume "
             "below the %d-contract standard unit. Spreads below 5c are unreliable: an empty book is "
             "served as a 0 ask." % UNIT_CONTRACTS)
    for s, r in t.items():
        for seg in r["segments"]:
            L.append("")
            L.append("### %s - %s..%s - %d brackets" % (s, seg["from"], seg["to"], seg["brackets"]))
            L.append("")
            L.append("| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |")
            L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
            for b in seg["bands"]:
                rng = "%d-%dc" % (b["lo"], min(100, b["hi"]))
                if not b["brackets"]:
                    L.append("| %s | %s | 0 | - | - | - | - | - | - |" % (b["band"], rng))
                    continue
                L.append("| %s | %s | %d | %s | %s | %s | %.0f%% | %.1fc | %.1fc |" % (
                    b["band"], rng, b["brackets"], fmt_int(round(b["vol_p25"])),
                    fmt_int(round(b["vol_median"])), fmt_int(round(b["vol_p90"])),
                    100 * b["share_under_unit"], b["spread_median"], b["spread_p75"]))
    return L


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
    L.append("| series | title | settles on | ladder | events | markets | candles | quoted window | tradeable window |")
    L.append("|---|---|---|---|---:|---:|---:|---|---|")
    for s, r in sorted(f["series"].items(), key=lambda kv: -(kv[1]["candles"] or 0)):
        src = ", ".join(r["settlement_sources"].keys()) or "-"
        win = ", ".join("%s..%s" % seg for seg in r["usable_segments"]) or "none"
        twin = ", ".join("%s..%s" % seg for seg in r["tradeable_segments"]) or "none"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            s, (r["title"] or "")[:40], src[:40], r["ladder_kind"] or "?",
            r["n_events"] if r["n_events"] is not None else "?",
            r["n_markets"] if r["n_markets"] is not None else "?",
            fmt_int(r["candles"]), win, twin))
    L.append("")
    L.append("`quoted window` = contiguous months in which at least %d%% of that month's markets "
             "returned candles AND the month averaged at least %d candles per market (someone was "
             "quoting). `tradeable window` = quoted months whose MEDIAN bracket had lifetime volume of "
             "at least %d contracts (someone was trading). Candle density is not depth: the 2022-24 "
             "KXWTI era is quoted but mostly not tradeable." %
             (int(100 * USABLE_SHARE), MIN_CANDLES_PER_MARKET, MIN_MEDIAN_VOLUME))

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
        tag = " (exchange-settled: CME/ICE option is a candidate hedge)" if is_exchange_source(src) else ""
        L.append("- **%s**%s: %s" % (src, tag, ", ".join(sorted(ss))))

    L.append("")
    L.append("## Databento shortlist")
    L.append("")
    short = [(s, r) for s, r in f["series"].items()
             if r["hedgeable_source"] and r["tradeable_months"] >= MIN_USABLE_MONTHS]
    if short:
        L.append("Series whose dominant settlement source is an exchange, with at least %d TRADEABLE months "
                 "(median bracket volume >= %d contracts):" % (MIN_USABLE_MONTHS, MIN_MEDIAN_VOLUME))
        L.append("")
        for s, r in sorted(short, key=lambda kv: -(kv[1]["candles"] or 0)):
            segs = ", ".join("%s..%s" % seg for seg in r["tradeable_segments"])
            qsegs = ", ".join("%s..%s" % seg for seg in r["usable_segments"])
            L.append("- **%s** (%s) tradeable %s; quoted %s; %s candles; front-month contracts seen: %s" % (
                s, r["dominant_source"], segs, qsegs, fmt_int(r["candles"]),
                ", ".join("%s (%d)" % kv for kv in r["front_month_contracts"].items() if kv[0]) or "-"))
        L.append("")
        L.append("Buy CME options history covering those windows (plus a month either side for the "
                 "density fit warm-up). Everything else settles on an aggregated index or has no "
                 "usable window yet.")
    else:
        L.append("No series meets both criteria yet (dominant exchange settlement source AND >= %d tradeable months)." % MIN_USABLE_MONTHS)

    if f.get("tails") is not None:
        L.extend(render_tails(f["tails"]))
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
        L.append("| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|")
        live_set = {m for seg in r["usable_segments"] for m in r["months"] if seg[0] <= m <= seg[1]}
        trade_set = {m for seg in r["tradeable_segments"] for m in r["months"] if seg[0] <= m <= seg[1]}
        for m, v in r["months"].items():
            zero = v["markets"] - v["with_candles"]
            per = v["candles"] / v["markets"] if v["markets"] else 0.0
            vm, vp, vz = v.get("vol_median"), v.get("vol_p90"), v.get("vol_zero_share")
            L.append("| %s | %d | %d | %s | %.0f | %s | %s | %s | %s | %s |" % (
                m, v["markets"], zero, fmt_int(v["candles"]), per,
                fmt_int(round(vm)) if vm is not None else "-",
                fmt_int(round(vp)) if vp is not None else "-",
                ("%.0f%%" % (100 * vz)) if vz is not None else "-",
                "yes" if m in live_set else "", "yes" if m in trade_set else ""))
    L.append("")
    return "\n".join(L)


def write_findings(store: Store, path: Optional[Path] = None, tails: bool = False) -> Path:
    path = Path(path) if path else store.root / "FINDINGS.md"
    f = build(store)
    if tails:
        f["tails"] = tail_depth(store, f)
    kc.atomic_write_text(path, render(f, store.root))
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data")
    ap.add_argument("--tails", action="store_true",
                    help="add the tail-depth section for shortlisted series (reads candles)")
    a = ap.parse_args(argv)
    p = write_findings(Store(Path(a.out)), tails=a.tails)
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
