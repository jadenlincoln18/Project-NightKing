#!/usr/bin/env python3
"""
verify.py - validate what is STORED, never what was logged.

A previous smoke test passed while every bid and ask was null because it only
counted rows. This reads the parquet and the manifest and checks column
population, value ranges, dtypes, duplicates, and manifest/file agreement.

  FAIL  -> exit 1 (the store must not be used)
  WARN  -> printed, exit 0 (exit 1 with --strict)

Usage
  python3 verify.py                        # data/
  python3 verify.py --out data_smoke
  python3 verify.py --strict
  python3 verify.py --crosscheck data/wtiw # compare with an old-layout pull (report only)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import kalshi_common as kc
from kalshi_common import Store, fmt_int

NULL_SHARE_MAX = 0.01          # bid/ask OHLC nulls allowed overall
NEG_SPREAD_SHARE_MAX = 0.001   # ask_close < bid_close rows allowed
BIDASK_COLS = [c for c in kc.CANDLE_FLOATS if c.startswith(("yes_bid_", "yes_ask_"))]
PRICE_COLS = [c for c in kc.CANDLE_FLOATS if c.startswith(("yes_bid_", "yes_ask_", "price_"))]


class Report:
    def __init__(self) -> None:
        self.items: List[Dict[str, str]] = []

    def add(self, level: str, check: str, detail: str = "") -> None:
        self.items.append({"level": level, "check": check, "detail": detail})
        print("%-4s %-38s %s" % (level, check, detail))

    def ok(self, check: str, detail: str = "") -> None:
        self.add("PASS", check, detail)

    def warn(self, check: str, detail: str = "") -> None:
        self.add("WARN", check, detail)

    def fail(self, check: str, detail: str = "") -> None:
        self.add("FAIL", check, detail)

    def n(self, level: str) -> int:
        return sum(1 for i in self.items if i["level"] == level)


def _candle_files(store: Store, period: Optional[int]) -> List[Path]:
    base = store.pq / "kalshi_candles"
    if not base.exists():
        return []
    files = sorted(base.rglob("part.parquet"))
    if period is not None:
        files = [f for f in files if ("period=%d" % period) in f.parts]
    return files


def _parts(path: Path) -> Dict[str, str]:
    out = {}
    for p in path.parts:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k] = v
    return out


def check_candles(store: Store, rep: Report, period: Optional[int], markets_df) -> Dict[str, Any]:
    import pandas as pd
    files = _candle_files(store, period)
    stats: Dict[str, Any] = {"files": len(files), "rows": 0, "null_bidask_cells": 0,
                             "bidask_cells": 0, "neg_spread": 0, "spread_rows": 0,
                             "out_of_range": 0, "dupes": 0, "per_series": defaultdict(
                                 lambda: {"files": 0, "rows": 0, "tickers": 0, "null_rows": 0,
                                          "neg_spread": 0})}
    ticker_rows: Dict[str, int] = {}
    ticker_file: Dict[str, Path] = {}
    ts_range: Dict[str, tuple] = {}
    bad_schema = []
    all_null_files = []
    lifetimes = {}
    if markets_df is not None and not markets_df.empty:
        for r in markets_df[["ticker", "open_time_epoch", "close_time_epoch"]].itertuples(index=False):
            lifetimes[r.ticker] = (r.open_time_epoch, r.close_time_epoch)
    ts_out = 0
    for f in files:
        parts = _parts(f)
        df = pd.read_parquet(f)
        ps = stats["per_series"][parts.get("series", "?")]
        ps["files"] += 1
        if list(df.columns) != kc.CANDLE_COLUMNS:
            bad_schema.append("%s columns %s" % (f, list(df.columns)[:6]))
            continue
        for c in kc.CANDLE_INTS:
            if str(df[c].dtype) != "int64":
                bad_schema.append("%s %s dtype %s" % (f.parent.name, c, df[c].dtype))
        for c in kc.CANDLE_FLOATS:
            if str(df[c].dtype) != "float64":
                bad_schema.append("%s %s dtype %s" % (f.parent.name, c, df[c].dtype))
        if not str(df["dt"].dtype).startswith("datetime64[ns, UTC]"):
            bad_schema.append("%s dt dtype %s" % (f.parent.name, df["dt"].dtype))
        n = len(df)
        stats["rows"] += n
        ps["rows"] += n
        if n == 0:
            continue
        for col in kc.BIDASK_CLOSE:
            if df[col].isna().all():
                all_null_files.append("%s/%s %s all null" % (parts.get("series"), parts.get("event"), col))
        stats["bidask_cells"] += n * len(BIDASK_COLS)
        stats["null_bidask_cells"] += int(df[BIDASK_COLS].isna().sum().sum())
        ps["null_rows"] += int(df[list(kc.BIDASK_CLOSE)].isna().any(axis=1).sum())
        vals = df[PRICE_COLS]
        stats["out_of_range"] += int(((vals < 0) | (vals > 100)).sum().sum())
        both = df["yes_ask_close"].notna() & df["yes_bid_close"].notna()
        neg = int((df.loc[both, "yes_ask_close"] < df.loc[both, "yes_bid_close"]).sum())
        stats["neg_spread"] += neg
        ps["neg_spread"] += neg
        stats["spread_rows"] += int(both.sum())
        stats["dupes"] += int(df.duplicated(["ticker", "ts"]).sum())
        g = df.groupby("ticker")["ts"]
        for tk, cnt in g.size().items():
            ticker_rows[tk] = int(cnt)
            ticker_file[tk] = f
        ps["tickers"] += len(g.size())
        for tk, (lo, hi) in zip(g.min().index, zip(g.min().values, g.max().values)):
            ts_range[tk] = (int(lo), int(hi))
            lt = lifetimes.get(tk)
            if lt and lt[0] is not None and lt[1] is not None and not pd.isna(lt[0]) and not pd.isna(lt[1]):
                per = int(df["period_min"].iloc[0]) * 60
                if int(lo) < int(lt[0]) - per or int(hi) > int(lt[1]) + per:
                    ts_out += 1

    if not files:
        rep.warn("candles: files", "no candle parquet files found")
    else:
        rep.ok("candles: files", "%d files, %s rows" % (len(files), fmt_int(stats["rows"])))
    if bad_schema:
        rep.fail("candles: schema/dtypes", "; ".join(bad_schema[:5]))
    elif files:
        rep.ok("candles: schema/dtypes", "all files match CANDLE_COLUMNS and dtypes")
    if all_null_files:
        rep.fail("candles: bid/ask populated", "%d file(s) with an all-null bid or ask close: %s"
                 % (len(all_null_files), "; ".join(all_null_files[:5])))
    elif stats["rows"]:
        share = stats["null_bidask_cells"] / max(1, stats["bidask_cells"])
        if share > NULL_SHARE_MAX:
            rep.fail("candles: bid/ask populated", "%.2f%% of bid/ask OHLC cells are null (max %.1f%%)"
                     % (100 * share, 100 * NULL_SHARE_MAX))
        else:
            rep.ok("candles: bid/ask populated", "%.3f%% null bid/ask cells" % (100 * share))
    if stats["out_of_range"]:
        rep.fail("candles: prices in [0,100]", "%d cells outside" % stats["out_of_range"])
    elif stats["rows"]:
        rep.ok("candles: prices in [0,100]")
    if stats["spread_rows"]:
        share = stats["neg_spread"] / stats["spread_rows"]
        if share > NEG_SPREAD_SHARE_MAX:
            rep.fail("candles: ask_close >= bid_close", "%d rows (%.3f%%) have ask < bid"
                     % (stats["neg_spread"], 100 * share))
        else:
            rep.ok("candles: ask_close >= bid_close", "%d rows (%.4f%%) crossed"
                   % (stats["neg_spread"], 100 * share))
    if stats["dupes"]:
        rep.fail("candles: unique (ticker, ts)", "%d duplicate rows" % stats["dupes"])
    elif stats["rows"]:
        rep.ok("candles: unique (ticker, ts)")
    if ts_out:
        rep.warn("candles: ts within market lifetime", "%d tickers have candles outside open..close" % ts_out)
    elif stats["rows"] and lifetimes:
        rep.ok("candles: ts within market lifetime")
    stats["ticker_rows"] = ticker_rows
    stats["ticker_file"] = ticker_file
    return stats


def check_manifest(store: Store, rep: Report, period: Optional[int], cstats: Dict[str, Any],
                   markets_df) -> None:
    entries = [e for e in store.entries.values() if period is None or e.get("period") == period]
    if not store.manifest_jsonl.exists():
        rep.fail("manifest: present", "%s missing" % store.manifest_jsonl)
        return
    if not entries:
        rep.warn("manifest: entries", "no entries for period %s" % period)
        return
    counts = Counter(e.get("status") for e in entries)
    rep.ok("manifest: entries", "%d entries: %s" % (len(entries), dict(counts)))
    for e in entries:
        if "fetch_ok" not in e or "status" not in e:
            rep.fail("manifest: schema", "entry without fetch_ok/status: %s" % e.get("key"))
            break
    else:
        rep.ok("manifest: schema", "every entry has status + fetch_ok + http_live/http_hist")
    ticker_rows = cstats.get("ticker_rows", {})
    mismatch, missing = [], []
    for e in entries:
        if e.get("status") != "ok":
            if e.get("ticker") in ticker_rows and e.get("rows", 0) == 0:
                mismatch.append("%s status=%s but %d rows stored" % (e["ticker"], e["status"], ticker_rows[e["ticker"]]))
            continue
        have = ticker_rows.get(e["ticker"])
        if have is None:
            missing.append(e["ticker"])
        elif have != int(e.get("rows") or 0):
            mismatch.append("%s manifest=%s parquet=%s" % (e["ticker"], e.get("rows"), have))
    if missing:
        rep.fail("manifest: ok entries have files", "%d ok tickers without stored rows: %s"
                 % (len(missing), missing[:5]))
    elif entries:
        rep.ok("manifest: ok entries have files")
    if mismatch:
        rep.fail("manifest: rows match parquet", "%d mismatches: %s" % (len(mismatch), mismatch[:4]))
    else:
        rep.ok("manifest: rows match parquet")
    errs = [e for e in entries if e.get("status") == "error"]
    if errs:
        rep.warn("manifest: errors", "%d markets with status=error (resume retries them): %s"
                 % (len(errs), ", ".join("%s[%s]" % (e["ticker"], e.get("error"))[:60] for e in errs[:6])))
    else:
        rep.ok("manifest: errors", "no status=error entries")
    if markets_df is not None and not markets_df.empty:
        known = set(markets_df["ticker"])
        unknown = sorted({e["ticker"] for e in entries if e["ticker"] not in known})
        if unknown:
            rep.fail("manifest: tickers in markets table", "%d candle tickers absent from markets table: %s"
                     % (len(unknown), unknown[:5]))
        else:
            rep.ok("manifest: tickers in markets table")
    by_series = defaultdict(Counter)
    for e in entries:
        by_series[e.get("series")][e.get("status")] += 1
    zero = [s for s, c in by_series.items() if c.get("ok", 0) == 0]
    if zero:
        rep.warn("manifest: series with candles", "series with zero ok markets: %s" % zero[:10])


def check_markets(store: Store, rep: Report, markets_df) -> None:
    import pandas as pd
    if markets_df is None or markets_df.empty:
        rep.fail("markets: table", "parquet/kalshi_markets is missing or empty")
        return
    missing_cols = [c for c in kc.MARKET_TYPED if c not in markets_df.columns]
    if missing_cols:
        rep.fail("markets: columns", "missing %s" % missing_cols)
    else:
        rep.ok("markets: columns", "%d rows, %d columns" % (len(markets_df), len(markets_df.columns)))
    ss = markets_df["settlement_sources"].map(lambda v: not kc.is_empty(v) and v not in ("[]", "null"))
    if not ss.any():
        rep.fail("markets: settlement_sources", "empty for every market")
    else:
        rep.ok("markets: settlement_sources", "%.1f%% populated; sources: %s"
               % (100 * ss.mean(), dict(Counter(markets_df["settlement_source_name"].dropna()).most_common(6))))
    settled = markets_df[markets_df["status"].isin(["settled", "finalized"])]
    if len(settled):
        ev = settled["expiration_value"].map(lambda v: not kc.is_empty(v))
        if ev.mean() < 0.99:
            rep.warn("markets: settled have expiration_value", "%.1f%% of %d settled markets"
                     % (100 * ev.mean(), len(settled)))
        else:
            rep.ok("markets: settled have expiration_value", "%.1f%% of %d" % (100 * ev.mean(), len(settled)))
        st = settled["settlement_ts"].map(lambda v: not kc.is_empty(v))
        if st.mean() < 0.99:
            rep.warn("markets: settled have settlement_ts", "%.1f%% of %d" % (100 * st.mean(), len(settled)))
        else:
            rep.ok("markets: settled have settlement_ts", "%.1f%%" % (100 * st.mean()))
    me_missing = markets_df["mutually_exclusive"].isna().mean()
    if me_missing > 0:
        rep.warn("markets: mutually_exclusive present", "%.1f%% missing (ladder kind fell back to labels)"
                 % (100 * me_missing))
    else:
        rep.ok("markets: mutually_exclusive present", "kinds: %s" % dict(Counter(markets_df["ladder_kind"])))
    conf = markets_df["merge_conflicts"].map(lambda v: isinstance(v, str) and v not in ("", "[]"))
    if conf.any():
        ex = markets_df.loc[conf, ["ticker", "merge_conflicts"]].head(5).values.tolist()
        rep.warn("markets: merge conflicts", "%d markets: %s" % (int(conf.sum()), ex))
    else:
        rep.ok("markets: merge conflicts", "none")
    # merge must never lose a settlement value that either raw record carried
    lost = []
    raw_keys: set = set()
    for series in sorted(markets_df["series"].dropna().unique()):
        have = {}
        for suffix in ("live", "hist"):
            raw = store.load_raw(Path("markets") / ("%s.%s.json.gz" % (series, suffix)))
            for m in (raw or {}).get("markets") or []:
                raw_keys.update(kc.flatten_record(m).keys())
                if not kc.is_empty(m.get("expiration_value")):
                    have[m.get("ticker")] = m.get("expiration_value")
        if not have:
            continue
        sub = markets_df[markets_df["series"] == series].set_index("ticker")
        for tk, v in have.items():
            if tk in sub.index and kc.is_empty(sub.at[tk, "expiration_value"]):
                lost.append(tk)
    if lost:
        rep.fail("markets: merge kept expiration_value", "%d markets lost it: %s" % (len(lost), lost[:5]))
    else:
        rep.ok("markets: merge kept expiration_value")
    if raw_keys:
        absent = sorted(k for k in raw_keys if k not in markets_df.columns and not k.startswith("_"))
        if absent:
            rep.warn("markets: raw keys captured", "raw fields absent from table: %s" % absent[:10])
        else:
            rep.ok("markets: raw keys captured", "every raw market field has a column")


def per_series_table(store: Store, cstats: Dict[str, Any], period: Optional[int]) -> None:
    print("\n%-18s %6s %9s %8s %6s %6s %6s %5s %9s %8s" %
          ("series", "files", "rows", "tickers", "ok", "empty", "nf", "err", "nullrows", "neg"))
    by = defaultdict(Counter)
    for e in store.entries.values():
        if period is None or e.get("period") == period:
            by[e.get("series")][e.get("status")] += 1
    for s in sorted(set(cstats["per_series"]) | set(by)):
        ps = cstats["per_series"].get(s) or {"files": 0, "rows": 0, "tickers": 0, "null_rows": 0, "neg_spread": 0}
        c = by.get(s, Counter())
        print("%-18s %6d %9s %8d %6d %6d %6d %5d %9d %8d" %
              (s, ps["files"], fmt_int(ps["rows"]), ps["tickers"], c.get("ok", 0), c.get("empty", 0),
               c.get("not_found", 0), c.get("error", 0), ps["null_rows"], ps["neg_spread"]))


def crosscheck(store: Store, old_dir: Path, period: Optional[int]) -> None:
    """Compare against an OLD-layout pull (per-market parquet files under
    parquet/kalshi_candles/series=S/event=E/<ticker>.parquet). Report only."""
    import pandas as pd
    print("\n" + "=" * 78)
    print("CROSSCHECK against %s (old layout, read-only)" % old_dir)
    print("=" * 78)
    base = old_dir / "parquet" / "kalshi_candles"
    files = [f for f in base.rglob("*.parquet") if f.name != "part.parquet"] if base.exists() else []
    if not files:
        print("no old-layout candle files under %s" % base)
        return
    old_frames = []
    for f in files:
        try:
            d = pd.read_parquet(f)
        except Exception as e:                                        # noqa: BLE001
            print("  unreadable %s: %s" % (f, e))
            continue
        if "ticker" not in d.columns:
            d["ticker"] = f.stem
        old_frames.append(d)
    if not old_frames:
        return
    old = pd.concat(old_frames, ignore_index=True)
    if period is not None and "period_min" in old.columns:
        old = old[old["period_min"] == period]
    new_files = _candle_files(store, period)
    new = pd.concat([pd.read_parquet(f) for f in new_files], ignore_index=True) if new_files else kc.empty_candle_frame()
    common = sorted(set(old["ticker"]) & set(new["ticker"]))
    print("old: %d files, %s rows, %d tickers" % (len(files), fmt_int(len(old)), old["ticker"].nunique()))
    print("new: %d files, %s rows, %d tickers" % (len(new_files), fmt_int(len(new)), new["ticker"].nunique()))
    print("overlapping tickers: %d" % len(common))
    if not common:
        return
    o = old[old["ticker"].isin(common)]
    n = new[new["ticker"].isin(common)]
    for col in ("yes_bid_close", "yes_ask_close"):
        if col in o.columns:
            print("  old %-14s null share %.2f%%   new %.2f%%"
                  % (col, 100 * o[col].isna().mean(), 100 * n[col].isna().mean()))
    j = o.merge(n, on=["ticker", "ts"], suffixes=("_old", "_new"))
    print("rows joined on (ticker, ts): %s of old %s / new %s" % (fmt_int(len(j)), fmt_int(len(o)), fmt_int(len(n))))
    for col in ("yes_bid_close", "yes_ask_close"):
        a, b = col + "_old", col + "_new"
        if a in j.columns and b in j.columns:
            both = j[a].notna() & j[b].notna()
            if both.any():
                eq = (abs(j.loc[both, a] - j.loc[both, b]) < 1e-6).mean()
                print("  %-14s exact match on %s comparable rows: %.2f%%" % (col, fmt_int(int(both.sum())), 100 * eq))
    rc_old = o.groupby("ticker").size()
    rc_new = n.groupby("ticker").size()
    agree = (rc_old == rc_new.reindex(rc_old.index)).mean()
    print("per-ticker row counts agree: %.1f%%" % (100 * agree))


def run(root: Path, strict: bool = False, period: Optional[int] = None,
        crosscheck_dir: Optional[Path] = None) -> int:
    root = Path(root)
    print("=" * 78)
    print("VERIFY %s%s" % (root, "" if period is None else "  (period=%d)" % period))
    print("=" * 78)
    if not root.exists():
        print("FAIL store: %s does not exist" % root)
        return 1
    store = Store(root)
    rep = Report()
    markets_df = store.read_all("kalshi_markets")
    cstats = check_candles(store, rep, period, markets_df)
    check_manifest(store, rep, period, cstats, markets_df)
    check_markets(store, rep, markets_df)
    ev = store.read_all("kalshi_events")
    if ev is None or ev.empty:
        rep.warn("events: table", "parquet/kalshi_events missing or empty")
    else:
        me = ev["mutually_exclusive"].isna().mean() if "mutually_exclusive" in ev.columns else 1.0
        rep.ok("events: table", "%d events, mutually_exclusive missing %.1f%%" % (len(ev), 100 * me))
    per_series_table(store, cstats, period)
    if crosscheck_dir:
        crosscheck(store, Path(crosscheck_dir), period)
    nf, nw = rep.n("FAIL"), rep.n("WARN")
    print("\n%s  (%d FAIL, %d WARN, %d PASS)%s" % (
        "FAIL" if nf or (strict and nw) else "PASS", nf, nw, rep.n("PASS"),
        "  [--strict: warnings fail]" if strict and nw else ""))
    return 1 if nf or (strict and nw) else 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data")
    ap.add_argument("--period", type=int, default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--crosscheck", default=None, help="old-layout data dir to compare against")
    a = ap.parse_args(argv)
    return run(Path(a.out), a.strict, a.period, Path(a.crosscheck) if a.crosscheck else None)


if __name__ == "__main__":
    sys.exit(main())
