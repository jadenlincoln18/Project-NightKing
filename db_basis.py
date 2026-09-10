#!/usr/bin/env python3
"""
db_basis.py - step 1 of the Databento brief: the ICE/NYMEX basis test (~$0.41).

Kalshi settles WTI on ICE's daily settlement; the only reachable hedge is a
NYMEX option. This measures the DISTRIBUTION of (ICE settle - NYMEX settle)
on every Kalshi settlement date, two ways:
  c0   against the NYMEX front month as Databento's continuous CL.c.0 sees it
  fm   against the exact NYMEX contract named by Kalshi's front_month_contract
and reports where the two disagree (a roll-date mismatch shows up here).

Pulls (quoted first, dry run by default):
  CL.c.0  statistics  continuous   ~$0.01   (brief's spec)
  CL.FUT  statistics  parent       ~$0.40   (every CL contract: exact-month join)

Usage
  python3 db_basis.py                 # dry run: plan + quotes
  python3 db_basis.py --execute       # buy, join, write FINDINGS_BASIS.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import db_common as dc
from db_common import log


def settlement_table(stats, label: str):
    """statistics -> one settlement price per (ET date, contract)."""
    import pandas as pd
    if stats is None or stats.empty:
        return pd.DataFrame(columns=["settle_date", "contract", "settle", "ts_event"])
    s = stats[stats["stat_type"] == dc.STAT_SETTLEMENT].copy()
    if s.empty:
        log.error("%s: no SETTLEMENT_PRICE (stat_type=%d) records; stat types seen: %s",
                  label, dc.STAT_SETTLEMENT, sorted(stats["stat_type"].unique().tolist()))
        return pd.DataFrame(columns=["settle_date", "contract", "settle", "ts_event"])
    ts = pd.to_datetime(s["ts_ref"] if "ts_ref" in s.columns and s["ts_ref"].notna().any() else s["ts_event"], utc=True)
    s["settle_date"] = ts.dt.tz_convert(dc.ET).dt.date
    s["contract"] = s["symbol"].astype(str)
    s["settle"] = pd.to_numeric(s["price"], errors="coerce")
    s = s.sort_values("ts_event").drop_duplicates(["settle_date", "contract"], keep="last")
    return s[["settle_date", "contract", "settle", "ts_event"]].reset_index(drop=True)


def describe(x) -> Dict[str, Any]:
    import numpy as np
    x = np.asarray([v for v in x if v == v], dtype=float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
            "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0, "min": float(x.min()), "max": float(x.max()),
            "p5": float(np.percentile(x, 5)), "p95": float(np.percentile(x, 95)),
            "abs_p95": float(np.percentile(np.abs(x), 95))}


def verdict(d: Dict[str, Any]) -> str:
    """Against a $1-wide Kalshi bracket."""
    if d.get("n", 0) < 5:
        return "insufficient data"
    if abs(d["mean"]) < 0.05 and d["sd"] < 0.10 and d["abs_p95"] < 0.25:
        return "tight"
    if abs(d["mean"]) < 0.15 and d["sd"] < 0.30 and d["abs_p95"] < 0.60:
        return "meaningful-but-stable"
    return "too wide"


def build(ev, c0, fut):
    """Join Kalshi ICE settlements to NYMEX settlements."""
    import pandas as pd
    c0t = settlement_table(c0, "CL.c.0").rename(columns={"contract": "c0_contract", "settle": "nymex_c0"})
    futt = settlement_table(fut, "CL.FUT").rename(columns={"contract": "cl_contract", "settle": "nymex_fm"})
    j = ev.merge(c0t[["settle_date", "c0_contract", "nymex_c0"]], on="settle_date", how="left")
    j = j.merge(futt[["settle_date", "cl_contract", "nymex_fm"]], on=["settle_date", "cl_contract"], how="left")
    j["basis_c0"] = j["expiration_value"] - j["nymex_c0"]
    j["basis_fm"] = j["expiration_value"] - j["nymex_fm"]
    j["roll_mismatch"] = j["cl_contract"].notna() & j["c0_contract"].notna() & (j["cl_contract"] != j["c0_contract"])
    return j, c0t, futt


def render(j, c0t, futt, stats_types: Dict[str, Any], costs: Dict[str, float]) -> str:
    import pandas as pd
    L: List[str] = []
    L.append("# FINDINGS_BASIS - ICE (Kalshi settlement) vs NYMEX (CL) daily settlement")
    L.append("")
    L.append("Generated %s. Kalshi `expiration_value` is the realised ICE daily settlement per event; "
             "NYMEX settlements come from Databento `GLBX.MDP3` `statistics` records with "
             "`stat_type = %d` (SETTLEMENT_PRICE). Both settle at 14:30 ET." % (dc.now_iso(), dc.STAT_SETTLEMENT))
    L.append("")
    L.append("Cost of this test: %s." % ", ".join("$%.2f %s" % (v, k) for k, v in costs.items()))
    L.append("")
    have = j[j["expiration_value"].notna()]
    L.append("Kalshi events with a settlement value: %d (%s). Joined to a NYMEX c.0 settlement: %d; "
             "to the exact front-month contract: %d (Kalshi names the contract on %d events)." % (
                 len(have), ", ".join("%s %d" % (s, n) for s, n in have["series"].value_counts().items()),
                 int(have["nymex_c0"].notna().sum()), int(have["nymex_fm"].notna().sum()),
                 int(have["cl_contract"].notna().sum())))
    L.append("")
    L.append("## Distribution of ICE - NYMEX ($/bbl), by series")
    L.append("")
    L.append("| series | basis | n | mean | median | sd | min | p5 | p95 | max | verdict |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    verdicts = {}
    for s, g in have.groupby("series"):
        for col, label in (("basis_c0", "vs CL.c.0"), ("basis_fm", "vs named front month")):
            d = describe(g[col])
            v = verdict(d)
            verdicts[(s, col)] = v
            if d["n"]:
                L.append("| %s | %s | %d | %+.3f | %+.3f | %.3f | %+.2f | %+.3f | %+.3f | %+.2f | %s |" % (
                    s, label, d["n"], d["mean"], d["median"], d["sd"], d["min"], d["p5"], d["p95"], d["max"], v))
            else:
                L.append("| %s | %s | 0 | - | - | - | - | - | - | - | %s |" % (s, label, v))
    L.append("")
    L.append("Verdict thresholds against a $1-wide bracket: **tight** = |mean| < 0.05, sd < 0.10, "
             "95th pct of |basis| < 0.25; **meaningful-but-stable** = |mean| < 0.15, sd < 0.30, "
             "95th pct < 0.60; else **too wide**.")
    L.append("")
    both = [v for (s, c), v in verdicts.items() if c == "basis_fm" and v != "insufficient data"]
    overall = ("too wide" if "too wide" in both else "meaningful-but-stable" if "meaningful-but-stable" in both
               else "tight" if both else "insufficient data")
    L.append("## Verdict: **%s**" % overall)
    L.append("")
    if overall == "tight":
        L.append("A NYMEX CL option is an adequate hedge for a Kalshi ICE-settled bracket on the current "
                 "account; no ICE licence needed for the basis. The residual is the number in the sd column.")
    elif overall == "meaningful-but-stable":
        L.append("The basis is a real cost but predictable: fold its mean into fair value and its sd into "
                 "position sizing; an ICE licence is not required to trade, but the edge must exceed the sd.")
    elif overall == "too wide":
        L.append("The cross-exchange residual is comparable to the bracket width. Do not trade a NYMEX hedge "
                 "against an ICE-settled bracket without an ICE-settled instrument.")
    L.append("")
    L.append("## Roll dates")
    L.append("")
    mm = have[have["roll_mismatch"]]
    known = have[have["cl_contract"].notna() & have["c0_contract"].notna()]
    L.append("Dates where Databento's continuous CL.c.0 was on a different contract than the one Kalshi "
             "names as its ICE front month: **%d of %d** comparable dates." % (len(mm), len(known)))
    if len(mm):
        L.append("")
        L.append("| date | series | Kalshi front month | CL.c.0 contract | basis vs c.0 | basis vs named |")
        L.append("|---|---|---|---|---:|---:|")
        for r in mm.itertuples():
            L.append("| %s | %s | %s | %s | %s | %s |" % (
                r.settle_date, r.series, r.cl_contract, r.c0_contract,
                ("%+.3f" % r.basis_c0) if r.basis_c0 == r.basis_c0 else "-",
                ("%+.3f" % r.basis_fm) if r.basis_fm == r.basis_fm else "-"))
        L.append("")
        L.append("On these dates the c.0 basis is contaminated by the calendar spread between two contract "
                 "months; the named-front-month basis is the one that measures the exchange difference.")
    # roll calendars
    L.append("")
    L.append("### Contract in use by date")
    L.append("")
    L.append("| contract | CL.c.0 first..last date | Kalshi front month first..last date |")
    L.append("|---|---|---|")
    c0r = have.dropna(subset=["c0_contract"]).groupby("c0_contract")["settle_date"].agg(["min", "max"])
    kr = have.dropna(subset=["cl_contract"]).groupby("cl_contract")["settle_date"].agg(["min", "max"])
    for ct in sorted(set(c0r.index) | set(kr.index)):
        a = "%s..%s" % (c0r.loc[ct, "min"], c0r.loc[ct, "max"]) if ct in c0r.index else "-"
        b = "%s..%s" % (kr.loc[ct, "min"], kr.loc[ct, "max"]) if ct in kr.index else "-"
        L.append("| %s | %s | %s |" % (ct, a, b))
    L.append("")
    L.append("## Largest |basis| days (named front month)")
    L.append("")
    L.append("| date | series | ICE (Kalshi) | NYMEX | basis |")
    L.append("|---|---|---:|---:|---:|")
    top = have.dropna(subset=["basis_fm"]).reindex(have["basis_fm"].abs().sort_values(ascending=False).index).head(10)
    for r in top.itertuples():
        L.append("| %s | %s | %.2f | %.2f | %+.3f |" % (r.settle_date, r.series, r.expiration_value, r.nymex_fm, r.basis_fm))
    L.append("")
    L.append("## Time series (named front month; c.0 where the name is missing)")
    L.append("")
    L.append("| date | series | ICE | NYMEX (named) | basis | NYMEX (c.0) | basis c.0 | c.0 contract |")
    L.append("|---|---|---:|---:|---:|---:|---:|---|")
    for r in have.sort_values("settle_ts").itertuples():
        f = lambda v, p="%.2f": (p % v) if v == v else "-"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r.settle_date, r.series, f(r.expiration_value), f(r.nymex_fm), f(r.basis_fm, "%+.3f"),
            f(r.nymex_c0), f(r.basis_c0, "%+.3f"), r.c0_contract or "-"))
    L.append("")
    L.append("## statistics schema contents (UNVERIFIED item 5, now measured)")
    L.append("")
    L.append("stat_type values seen on CL.c.0: %s. SETTLEMENT_PRICE = 3 carries the daily settlement; "
             "`ts_ref` is the session it refers to." % json.dumps(stats_types))
    L.append("")
    return "\n".join(L)


def plot(j, path: Path) -> Optional[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    have = j[j["expiration_value"].notna()].sort_values("settle_ts")
    fig, ax = plt.subplots(figsize=(11, 4))
    for s, g in have.groupby("series"):
        ax.plot(g["settle_ts"], g["basis_fm"], marker="o", ms=3, lw=0.8, label="%s vs named front month" % s)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("ICE - NYMEX ($/bbl)")
    ax.set_title("Kalshi ICE settlement minus NYMEX CL settlement, per Kalshi settlement date")
    ax.legend()
    fig.autofmt_xdate()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(dc.DEFAULT_OUT))
    ap.add_argument("--kalshi", default="data", help="Kalshi store root (reads kalshi_markets)")
    ap.add_argument("--since", default="2026-01-01", help="earliest Kalshi settlement to include")
    ap.add_argument("--max-cost", type=float, default=dc.DEFAULT_MAX_COST)
    ap.add_argument("--execute", action="store_true", help="actually buy (default: dry run)")
    ap.add_argument("--client", choices=["real", "fake"], default="real", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    out = Path(a.out)
    dc.setup_logging(str(out / "db.log"))
    dc.assert_env_gitignored()
    import pandas as pd
    ev = dc.kalshi_settlements(Path(a.kalshi), since=a.since)
    have = ev[ev["expiration_value"].notna()]
    if have.empty:
        print("no Kalshi events with expiration_value since %s" % a.since)
        return 2
    start = (pd.Timestamp(have["settle_date"].min()) - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    end = min(pd.Timestamp(have["settle_date"].max()) + pd.Timedelta(days=1),
              pd.Timestamp.utcnow().tz_localize(None).normalize()).strftime("%Y-%m-%d")
    print("Kalshi settlement dates: %d events with values, %s .. %s (%s)" % (
        len(have), have["settle_date"].min(), have["settle_date"].max(),
        ", ".join("%s %d" % (s, n) for s, n in have["series"].value_counts().items())))

    client = None
    if a.client == "fake":
        sys.path.insert(0, str(Path(__file__).parent / "tests"))
        from fake_databento import FakeHistorical
        client = FakeHistorical()
    dbc = dc.DBClient(out, max_cost=a.max_cost, execute=a.execute, client=client)
    c0 = dbc.pull("futures_stats_c0", "statistics", ["CL.c.0"], "continuous", start, end,
                  parquet_rel="futures_stats/symbol=CL.c.0/part.parquet")
    fut = dbc.pull("futures_stats_clfut", "statistics", ["CL.FUT"], "parent", start, end,
                   parquet_rel="futures_stats/symbol=CL.FUT/part.parquet")
    total = dbc.print_plan("BASIS TEST")
    if not a.execute:
        print("\ndry run complete. Re-run with --execute to buy ($%.2f) and write FINDINGS_BASIS.md" % total)
        return 0
    j, c0t, futt = build(ev, c0, fut)
    dc.write_parquet(j, out / "parquet" / "basis" / "part.parquet")
    types = {str(k): int(v) for k, v in c0["stat_type"].value_counts().sort_index().items()} if c0 is not None else {}
    costs = {p["name"]: p["cost"] for p in dbc.plan}
    txt = render(j, c0t, futt, types, costs)
    png = plot(j, out / "basis.png")
    if png:
        txt += "\n![basis](basis.png)\n"
    dc.atomic_write_text(out / "FINDINGS_BASIS.md", txt)
    print("\n" + "\n".join(l for l in txt.splitlines()[:40]))
    print("\nwrote %s" % (out / "FINDINGS_BASIS.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
