#!/usr/bin/env python3
"""
db_pull.py - steps 2-5 of the Databento brief: option definitions, the root
question, TBBO, quote-density measurement, and the store.

Every request is quoted first; nothing is bought without --execute; a manifest
makes re-runs free.

Steps
  definition  pull `definition` for every WTI option root that exists (LO, the
              Mon/Wed/Fri weeklies, MCO); match expiry dates to the Kalshi
              settlement dates -> which roots, how many dates covered
  tbbo        pull `tbbo` for the matched roots over the Kalshi window; split
              by expiry; measure, per Kalshi date, how many strikes had a fresh
              quote in the last 30/60/120 minutes and whether both wings did
  findings    write FINDINGS_CHAIN.md with the root choice, the density table
              and the bbo-1m recommendation (with its quoted cost)

Usage
  python3 db_pull.py                          # dry run of everything: plan + total
  python3 db_pull.py --execute                # buy definitions + tbbo (~$13 all roots)
  python3 db_pull.py --roots LO1,LO2,LO3,LO4,LO5 --execute
  python3 db_pull.py --step findings          # re-render from what is on disk
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import db_common as dc
from db_common import log

WINDOWS_MIN = (30, 60, 120)
MIN_STRIKES = 8
MIN_WING = 3


# --------------------------------------------------------------------------
# definitions
# --------------------------------------------------------------------------

def parse_definitions(df, root: str):
    """definition rows -> one row per option instrument with parsed symbol fields."""
    import pandas as pd
    if df is None or df.empty:
        return pd.DataFrame(columns=["root", "raw_symbol", "instrument_id", "expiry_date", "strike", "right"])
    d = df.copy()
    sym_col = "raw_symbol" if "raw_symbol" in d.columns else "symbol"
    parsed = d[sym_col].map(dc.parse_option_symbol)
    # a parent request returns other products' instruments too (BTC/ETH/XPT options
    # arrived inside LO.OPT): keep only symbols whose root is the one requested
    keep = parsed.map(lambda x: bool(x) and x["root"] == root)
    d = d[keep].copy()
    if not keep.any():
        return pd.DataFrame(columns=["root", "raw_symbol", "instrument_id", "expiry_date", "strike", "right"])
    p = pd.DataFrame(list(parsed[keep]))
    d["root"] = p["root"].values
    d["right"] = p["right"].values
    d["strike"] = p["strike"].values
    d["contract"] = p["contract"].values
    exp = pd.to_datetime(d["expiration"], utc=True, errors="coerce")
    d["expiry_ts"] = exp
    d["expiry_date"] = exp.dt.tz_convert(dc.ET).dt.date
    if "strike_price" in d.columns:
        sp = pd.to_numeric(d["strike_price"], errors="coerce")
        bad = (sp.notna()) & ((sp - d["strike"]).abs() > 0.005)
        if bad.any():
            log.warning("%s: %d instruments where strike_price differs from the symbol's strike (using strike_price)",
                        root, int(bad.sum()))
            d.loc[bad, "strike"] = sp[bad]
    d = d.sort_values(["expiry_date", "strike", "right"]).drop_duplicates(["raw_symbol"] if sym_col == "raw_symbol" else ["symbol"], keep="last")
    return d


def expiry_table(defs):
    """Per (root, expiry_date): strike count and range."""
    g = defs.groupby(["root", "expiry_date"]).agg(instruments=("strike", "size"), strikes=("strike", "nunique"),
                                                   k_min=("strike", "min"), k_max=("strike", "max"),
                                                   calls=("right", lambda s: int((s == "C").sum())),
                                                   puts=("right", lambda s: int((s == "P").sum()))).reset_index()
    return g


def match_roots(exp_tab, ev) -> Tuple[Any, Dict[str, Any]]:
    """Which roots expire ON each Kalshi settlement date."""
    import pandas as pd
    dates = ev[["series", "event_ticker", "settle_date", "weekday"]].drop_duplicates()
    m = dates.merge(exp_tab, left_on="settle_date", right_on="expiry_date", how="left")
    cov = {}
    for s, g in m.groupby("series"):
        n_dates = g["settle_date"].nunique()
        matched = g.dropna(subset=["root"])
        by_root = matched.groupby("root")["settle_date"].nunique().sort_values(ascending=False)
        any_root = matched["settle_date"].nunique()
        by_wd = g.groupby("weekday").apply(lambda x: (x["settle_date"].nunique(), x.dropna(subset=["root"])["settle_date"].nunique()))
        cov[s] = {"dates": int(n_dates), "dates_with_any_expiry": int(any_root),
                  "by_root": {k: int(v) for k, v in by_root.items()},
                  "by_weekday": {k: {"dates": int(v[0]), "matched": int(v[1])} for k, v in by_wd.items()}}
    return m, cov


# --------------------------------------------------------------------------
# tbbo density
# --------------------------------------------------------------------------

def density_for_date(tb, defs_on_date, settle_ts, forward: Optional[float]) -> Dict[str, Any]:
    """tb: tbbo rows for instruments expiring on this date, this date only.
    Per strike (calls and puts pooled): the last quote before settle_ts."""
    import pandas as pd
    out: Dict[str, Any] = {"instruments": int(len(defs_on_date)), "strikes_listed": int(defs_on_date["strike"].nunique())}
    if tb is None or tb.empty:
        out.update({"records": 0, "strikes_quoted": 0, "median_age_min": None})
        for w in WINDOWS_MIN:
            out["strikes_%dm" % w] = 0
            out["below_%dm" % w] = 0
            out["above_%dm" % w] = 0
        out["clears"] = False
        return out
    t = tb[tb["ts_event"] <= settle_ts].copy()
    out["records"] = int(len(t))
    if t.empty:
        out.update({"strikes_quoted": 0, "median_age_min": None, "clears": False})
        for w in WINDOWS_MIN:
            out["strikes_%dm" % w] = out["below_%dm" % w] = out["above_%dm" % w] = 0
        return out
    last = t.sort_values("ts_event").groupby("strike")["ts_event"].last()
    age = (settle_ts - last).dt.total_seconds() / 60.0
    out["strikes_quoted"] = int(len(last))
    out["median_age_min"] = float(age.median())
    if forward is None or forward != forward:
        forward = float(t["strike"].median())
    out["forward_used"] = float(forward)
    for w in WINDOWS_MIN:
        fresh = age[age <= w]
        out["strikes_%dm" % w] = int(len(fresh))
        out["below_%dm" % w] = int((fresh.index < forward).sum())
        out["above_%dm" % w] = int((fresh.index > forward).sum())
    out["clears"] = bool(out["strikes_60m"] >= MIN_STRIKES and out["below_60m"] >= MIN_WING and out["above_60m"] >= MIN_WING)
    return out


def measure_density(tbbo_by_root: Dict[str, Any], defs, ev, forwards: Dict[Any, float]):
    """One row per (Kalshi event, root with an expiry on that date)."""
    import pandas as pd
    rows = []
    for r in ev.itertuples():
        d_on = defs[defs["expiry_date"] == r.settle_date]
        for root, dd in d_on.groupby("root"):
            tb = tbbo_by_root.get(root)
            sub = None
            if tb is not None and not tb.empty:
                syms = set(dd["raw_symbol"] if "raw_symbol" in dd.columns else dd["symbol"])
                sub = tb[tb["symbol"].isin(syms)]
                sub = sub[(sub["ts_event"] >= r.settle_ts - pd.Timedelta(hours=8))]
            rec = density_for_date(sub, dd, r.settle_ts, forwards.get(r.settle_date))
            rec.update({"series": r.series, "event_ticker": r.event_ticker, "settle_date": r.settle_date,
                        "weekday": r.weekday, "root": root})
            rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# tbbo pull, chunked by month when large (a 2.2M-record LO request 504'd)
# --------------------------------------------------------------------------

def month_chunks(start: str, end: str) -> List[Tuple[str, str]]:
    import pandas as pd
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    cur = s
    while cur < e:
        nxt = min((cur + pd.offsets.MonthBegin(1)).normalize(), e)
        if nxt <= cur:
            nxt = e
        out.append((cur.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d")))
        cur = nxt
    return out


def pull_tbbo(dbc, root: str, start: str, end: str, chunk_records: int):
    """One request per root, or one per calendar month when Databento reports more
    than `chunk_records` records (the gateway timed out on the 2.2M-record LO pull).
    Each chunk is its own manifest entry, so a failed month is retried alone."""
    import pandas as pd
    sym = root + ".OPT"
    try:
        n = dbc.record_count("tbbo", [sym], "parent", start, end)
    except Exception as e:                                               # noqa: BLE001
        log.warning("record_count %s failed (%s) - pulling unchunked", sym, str(e)[:80])
        n = 0
    if n <= chunk_records:
        return dbc.pull("tbbo_%s" % root, "tbbo", [sym], "parent", start, end,
                        parquet_rel="options_tbbo/root=%s/part.parquet" % root)
    chunks = month_chunks(start, end)
    log.info("%s tbbo has %s records - pulling in %d monthly chunks", sym, "{:,}".format(n), len(chunks))
    frames = []
    missing = 0
    for c0, c1 in chunks:
        df = dbc.pull("tbbo_%s_%s" % (root, c0[:7]), "tbbo", [sym], "parent", c0, c1,
                      parquet_rel="options_tbbo/root=%s/month=%s/part.parquet" % (root, c0[:7]))
        if df is None:
            missing += 1
        elif len(df):
            frames.append(df)
    if missing and dbc.execute:
        log.error("%s: %d monthly chunk(s) missing - density for those months will be understated until re-run",
                  sym, missing)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------
# findings
# --------------------------------------------------------------------------

def render_chain(cov: Dict[str, Any], exp_tab, dens, roots_used: List[str], costs: Dict[str, float],
                 upgrade_quote: Optional[Dict[str, Any]], resolve_note: str) -> str:
    L: List[str] = []
    L.append("# FINDINGS_CHAIN - which CME WTI option root, and is TBBO dense enough")
    L.append("")
    L.append("Generated %s. Cost of the pulls behind this file: %s." % (
        dc.now_iso(), ", ".join("$%.2f %s" % (v, k) for k, v in costs.items()) or "nothing bought yet"))
    L.append("")
    L.append("## Symbology (UNVERIFIED item 3, resolved)")
    L.append("")
    L.append(resolve_note)
    L.append("")
    L.append("## Root selection (UNVERIFIED item 1)")
    L.append("")
    if exp_tab is not None and len(exp_tab):
        L.append("Expiries listed per root inside the Kalshi window:")
        L.append("")
        L.append("| root | expiries | first | last | strikes per expiry (median) | strike range |")
        L.append("|---|---:|---|---|---:|---|")
        for root, g in exp_tab.groupby("root"):
            L.append("| %s | %d | %s | %s | %.0f | %.2f - %.2f |" % (
                root, len(g), g["expiry_date"].min(), g["expiry_date"].max(), g["strikes"].median(),
                g["k_min"].min(), g["k_max"].max()))
        L.append("")
    for s, c in cov.items():
        L.append("**%s**: %d settlement dates, %d have an option expiring that day." % (s, c["dates"], c["dates_with_any_expiry"]))
        L.append("")
        L.append("| weekday | dates | with an expiry |")
        L.append("|---|---:|---:|")
        for wd in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
            v = c["by_weekday"].get(wd)
            if v:
                L.append("| %s | %d | %d |" % (wd, v["dates"], v["matched"]))
        L.append("")
        L.append("dates covered per root: %s" % ", ".join("%s %d" % kv for kv in c["by_root"].items()))
        L.append("")
    L.append("**Roots to use: %s.** CME lists WTI weeklies expiring Monday (ML1-5), Wednesday (WL1-5) and "
             "Friday (LO1-5); there are no Tuesday or Thursday weeklies, so a Kalshi daily (KXWTI) settling on "
             "those days can only match the monthly LO on its own expiry day." % ", ".join(roots_used))
    L.append("")
    L.append("## TBBO quote density (UNVERIFIED item 2)")
    L.append("")
    if dens is None or dens.empty:
        L.append("No TBBO on disk yet (dry run, or the tbbo step was not executed).")
    else:
        L.append("Per Kalshi settlement date and root: strikes (calls and puts pooled) whose last TBBO quote "
                 "before 14:30 ET was within 30 / 60 / 120 minutes; wings counted against the NYMEX settlement "
                 "of the day (fallback: median quoted strike). `clears` = at least %d strikes within 60 minutes "
                 "with at least %d on each side." % (MIN_STRIKES, MIN_WING))
        L.append("")
        for s, g in dens.groupby("series"):
            n = g["event_ticker"].nunique()
            ok = g[g["clears"]]["event_ticker"].nunique()
            L.append("**%s**: %d dates with a matching expiry, **%d clear** the %d-strike / both-wings threshold "
                     "(%.0f%%)." % (s, n, ok, MIN_STRIKES, 100.0 * ok / n if n else 0))
            L.append("")
            L.append("| date | root | listed strikes | quoted (any) | 30m | 60m (below/above) | 120m | median age (min) | clears |")
            L.append("|---|---|---:|---:|---:|---|---:|---:|:---:|")
            for r in g.sort_values(["settle_date", "root"]).itertuples():
                L.append("| %s | %s | %d | %d | %d | %d (%d/%d) | %d | %s | %s |" % (
                    r.settle_date, r.root, r.strikes_listed, r.strikes_quoted, r.strikes_30m, r.strikes_60m,
                    r.below_60m, r.above_60m, r.strikes_120m,
                    ("%.0f" % r.median_age_min) if r.median_age_min is not None and r.median_age_min == r.median_age_min else "-",
                    "yes" if r.clears else ""))
            L.append("")
        tot = dens["event_ticker"].nunique()
        okk = dens[dens["clears"]]["event_ticker"].nunique()
        share = okk / tot if tot else 0.0
        L.append("## Verdict on TBBO")
        L.append("")
        if share >= 0.8:
            L.append("**TBBO is sufficient**: %d of %d dates clear the threshold. No bbo-1m upgrade needed." % (okk, tot))
        else:
            L.append("**TBBO is too sparse**: only %d of %d dates clear the threshold. TBBO samples in trade space, "
                     "so wing strikes go unquoted for hours. The bbo-1m upgrade, scoped to the matched settlement "
                     "dates only, is the fallback." % (okk, tot))
        if upgrade_quote:
            L.append("")
            L.append("bbo-1m scoped to the %d matched dates for roots %s: **$%.2f quoted** (%d requests)." % (
                upgrade_quote["dates"], ",".join(upgrade_quote["roots"]), upgrade_quote["total"], upgrade_quote["requests"]))
    L.append("")
    L.append("## Store notes")
    L.append("")
    L.append("`parquet/options_tbbo/root=R/` holds every record the parent request returned, including "
             "user-defined spread instruments (`UD:...`) that trade at net credits, so negative prices appear "
             "there. `parquet/options_tbbo_by_expiry/root=R/expiry=D/` is the outright-only view, joined to the "
             "definitions, which is what the smile fit should read. Bid and ask are `bid_px_00` / `ask_px_00` "
             "with sizes `bid_sz_00` / `ask_sz_00`; no mid is stored.")
    L.append("")
    L.append("## Timestamp alignment (UNVERIFIED item 4)")
    L.append("")
    L.append("Databento TBBO rows carry `ts_event` (matching-engine time) and `ts_recv` (capture time). "
             "`ts_event` is used. Kalshi 1-minute candles are keyed by `end_period_ts`, the END of the bar, so "
             "a Databento event at time t belongs to the Kalshi bar ending at ceil_minute(t); "
             "`db_common.kalshi_bar_end()` implements that. Kalshi settles at 14:30 ET (18:30 UTC in summer, "
             "19:30 in winter) - the Kalshi close_time is used per event rather than a fixed UTC offset.")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(dc.DEFAULT_OUT))
    ap.add_argument("--kalshi", default="data")
    ap.add_argument("--since", default="2026-01-01")
    ap.add_argument("--roots", default=",".join(dc.OPTION_ROOTS), help="candidate option roots (default: all that exist)")
    ap.add_argument("--step", choices=["all", "definition", "tbbo", "findings"], default="all")
    ap.add_argument("--max-cost", type=float, default=dc.DEFAULT_MAX_COST)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--chunk-records", type=int, default=500_000,
                    help="tbbo requests above this many records are pulled month by month")
    ap.add_argument("--client", choices=["real", "fake"], default="real", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    out = Path(a.out)
    dc.setup_logging(str(out / "db.log"))
    dc.assert_env_gitignored()
    import pandas as pd
    ev = dc.kalshi_settlements(Path(a.kalshi), since=a.since)
    start = (pd.Timestamp(ev["settle_date"].min()) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end = min(pd.Timestamp(ev["settle_date"].max()) + pd.Timedelta(days=1),
              pd.Timestamp.utcnow().tz_localize(None).normalize()).strftime("%Y-%m-%d")
    roots = [r.strip().upper() for r in a.roots.split(",") if r.strip()]
    print("Kalshi window %s..%s: %s" % (start, end, ", ".join("%s %d dates" % (s, g["settle_date"].nunique()) for s, g in ev.groupby("series"))))

    client = None
    if a.client == "fake":
        sys.path.insert(0, str(Path(__file__).parent / "tests"))
        from fake_databento import FakeHistorical
        client = FakeHistorical()
    dbc = dc.DBClient(out, max_cost=a.max_cost, execute=a.execute, client=client)

    # symbology note (free)
    resolve_note = ("`symbology.resolve(stype_in='parent')` puts child instruments in the response's `partial` "
                    "list, not in `result`; counting `result` reads as 0 mappings. Children per root in the window:")
    counts = {}
    for root in roots:
        try:
            kids = dbc.resolve_children(root + ".OPT", start, end)
            n_opt = sum(1 for k in kids if dc.parse_option_symbol(k))
            counts[root] = (len(kids), n_opt)
        except Exception as e:                                       # noqa: BLE001
            counts[root] = (0, 0)
            log.warning("resolve %s.OPT failed: %s", root, str(e)[:100])
    resolve_note += " " + ", ".join("%s %d (%d options, rest UD spreads)" % (r, c[0], c[1]) for r, c in counts.items())
    roots = [r for r in roots if counts.get(r, (0, 0))[1] > 0] or roots

    # ---- definitions
    defs_by_root = {}
    if a.step in ("all", "definition", "tbbo"):
        for root in roots:
            df = dbc.pull("definition_%s" % root, "definition", [root + ".OPT"], "parent", start, end,
                          parquet_rel="options_definition/root=%s/part.parquet" % root)
            if df is not None:
                defs_by_root[root] = parse_definitions(df, root)
    defs = pd.concat(defs_by_root.values(), ignore_index=True) if defs_by_root else None
    exp_tab, cov, matched_roots = None, {}, roots
    if defs is not None and len(defs):
        exp_tab = expiry_table(defs)
        m, cov = match_roots(exp_tab, ev)
        matched_roots = sorted({r for c in cov.values() for r in c["by_root"] if r in roots})
        print("\nroots with an expiry on a Kalshi date: %s" % ", ".join(matched_roots))

    # ---- tbbo for matched roots
    tbbo_by_root: Dict[str, Any] = {}
    if a.step in ("all", "tbbo"):
        for root in matched_roots:
            df = pull_tbbo(dbc, root, start, end, a.chunk_records)
            if df is not None:
                df = df.copy()
                df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
                p = df["symbol"].map(dc.parse_option_symbol)
                df["strike"] = p.map(lambda x: x["strike"] if x else None)
                df["right"] = p.map(lambda x: x["right"] if x else None)
                tbbo_by_root[root] = df

    total = dbc.print_plan("OPTIONS PULL")
    if not a.execute and a.step != "findings":
        print("\ndry run complete. Re-run with --execute to buy ($%.2f)." % total)
        return 0

    # ---- density + findings from what is on disk
    if defs is None:
        d = dc.read_all(out / "parquet" / "options_definition")
        if d is not None:
            defs = pd.concat([parse_definitions(g, r) for r, g in d.groupby("root")], ignore_index=True)
            exp_tab = expiry_table(defs)
            _, cov = match_roots(exp_tab, ev)
            matched_roots = sorted({r for c in cov.values() for r in c["by_root"] if r in roots})
    if not tbbo_by_root:
        t = dc.read_all(out / "parquet" / "options_tbbo")
        if t is not None:
            t = t[t["root"].isin(roots)]
            t["ts_event"] = pd.to_datetime(t["ts_event"], utc=True)
            p = t["symbol"].map(dc.parse_option_symbol)
            t["strike"] = p.map(lambda x: x["strike"] if x else None)
            t["right"] = p.map(lambda x: x["right"] if x else None)
            tbbo_by_root = {r: g for r, g in t.groupby("root")}
    forwards: Dict[Any, float] = {}
    bp = out / "parquet" / "basis" / "part.parquet"
    if bp.exists():
        b = pd.read_parquet(bp)
        for r in b.itertuples():
            v = r.nymex_fm if r.nymex_fm == r.nymex_fm else r.nymex_c0
            if v == v:
                forwards[r.settle_date] = float(v)
    dens = None
    if defs is not None and tbbo_by_root:
        dens = measure_density(tbbo_by_root, defs, ev, forwards)
        dc.write_parquet(dens, out / "parquet" / "chain_density" / "part.parquet")
        # split tbbo by expiry for the store layout the brief asks for
        for root, tb in tbbo_by_root.items():
            syms = defs[defs["root"] == root]
            symcol = "raw_symbol" if "raw_symbol" in syms.columns else "symbol"
            exp_of = dict(zip(syms[symcol], syms["expiry_date"]))
            tb = tb.copy()
            tb["expiry"] = tb["symbol"].map(exp_of)
            for exp, g in tb.dropna(subset=["expiry"]).groupby("expiry"):
                dc.write_parquet(g.drop(columns=["expiry"]),
                                 out / "parquet" / "options_tbbo_by_expiry" / ("root=%s" % root) / ("expiry=%s" % exp) / "part.parquet")
    upgrade = None
    if dens is not None and len(dens):
        share = dens[dens["clears"]]["event_ticker"].nunique() / max(1, dens["event_ticker"].nunique())
        if share < 0.8:
            reqs, tot_q = 0, 0.0
            for r in dens.drop_duplicates(["settle_date", "root"]).itertuples():
                d0 = pd.Timestamp(r.settle_date).strftime("%Y-%m-%d")
                d1 = (pd.Timestamp(r.settle_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                try:
                    tot_q += dbc.quote("bbo-1m", [r.root + ".OPT"], "parent", d0, d1)
                    reqs += 1
                except Exception as e:                               # noqa: BLE001
                    log.warning("bbo-1m quote failed for %s %s: %s", r.root, d0, str(e)[:80])
            upgrade = {"dates": dens["settle_date"].nunique(), "roots": sorted(dens["root"].unique()),
                       "total": tot_q, "requests": reqs}
    costs = {e["name"]: float(e["cost"]) for e in dbc.manifest.entries.values() if e.get("status") == "ok"}
    txt = render_chain(cov, exp_tab, dens, matched_roots, costs, upgrade, resolve_note)
    dc.atomic_write_text(out / "FINDINGS_CHAIN.md", txt)
    print("\nwrote %s" % (out / "FINDINGS_CHAIN.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
