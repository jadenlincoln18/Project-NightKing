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


def trade_date(s):
    """VERIFIED on the bought data: a SETTLEMENT_PRICE record's `ts_ref` is midnight
    UTC of the CME trade date (20:00 ET the evening before, when the Globex session
    opens). The UTC date of ts_ref IS the trade date; its ET date is one day early,
    which is the bug that turned the first basis run into a daily-move series.
    Fallback: the ET date of ts_event (the settlement is published ~14:30:50 ET)."""
    import pandas as pd
    ref = pd.to_datetime(s["ts_ref"], utc=True, errors="coerce") if "ts_ref" in s.columns else pd.Series([pd.NaT] * len(s), index=s.index)
    ev = pd.to_datetime(s["ts_event"], utc=True, errors="coerce")
    d = ref.dt.date.where(ref.notna(), ev.dt.tz_convert(dc.ET).dt.date)
    return d


def settlement_table(stats, label: str, id_to_symbol: Optional[Dict[int, str]] = None):
    """statistics -> one settlement price per (trade date, outright contract).
    The continuous symbol's `symbol` column says 'CL.c.0'; the contract comes from
    instrument_id via the CL.FUT pull (id_to_symbol). Spreads are dropped."""
    import pandas as pd
    cols = ["settle_date", "contract", "settle", "ts_event"]
    if stats is None or stats.empty:
        return pd.DataFrame(columns=cols)
    s = stats[stats["stat_type"] == dc.STAT_SETTLEMENT].copy()
    if s.empty:
        log.error("%s: no SETTLEMENT_PRICE (stat_type=%d) records; stat types seen: %s",
                  label, dc.STAT_SETTLEMENT, sorted(stats["stat_type"].unique().tolist()))
        return pd.DataFrame(columns=cols)
    s["settle_date"] = trade_date(s)
    sym = s["symbol"].astype(str)
    if id_to_symbol:
        mapped = s["instrument_id"].map(id_to_symbol)
        sym = mapped.where(mapped.notna(), sym)
    s["contract"] = sym
    s = s[s["contract"].map(lambda x: dc.parse_future_symbol(x) is not None)]
    s["settle"] = pd.to_numeric(s["price"], errors="coerce")
    s["ts_event"] = pd.to_datetime(s["ts_event"], utc=True)
    s = s.sort_values("ts_event").drop_duplicates(["settle_date", "contract"], keep="last")
    return s[cols].reset_index(drop=True)


def last_trade_dates(futt) -> Dict[str, Any]:
    """NYMEX last trading day per contract = last trade date with a settlement,
    for contracts that stopped settling inside the window."""
    if futt is None or futt.empty:
        return {}
    last = futt.groupby("contract")["settle_date"].max()
    window_end = futt["settle_date"].max()
    return {c: d for c, d in last.items() if d < window_end}


def prev_business_day(d):
    import pandas as pd
    t = pd.Timestamp(d) - pd.Timedelta(days=1)
    while t.weekday() >= 5:
        t -= pd.Timedelta(days=1)
    return t.date()


def infer_ice_front_month(settle_date, ltd: Dict[str, Any]) -> Optional[str]:
    """ICE WTI (WBS) ceases trading on the business day BEFORE the NYMEX CL last
    trading day. Kalshi references the earliest contract whose ICE expiry is
    strictly after the settlement date (VERIFIED: on the ICE expiry day itself
    Kalshi already names the next month). Weekend-only calendar: a holiday can
    shift the ICE expiry by a day, so inferred months are checked against the
    named ones and labelled `inferred`."""
    cands = []
    for c, d in ltd.items():
        p = dc.parse_future_symbol(c)
        if not p:
            continue
        ice_exp = prev_business_day(d)
        if ice_exp > settle_date:
            cands.append((p["year"], p["month"], c))
    if not cands:
        return None
    return sorted(cands)[0][2]


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
    """Join Kalshi ICE settlements to NYMEX settlements, two ways."""
    import pandas as pd
    futt_raw = settlement_table(fut, "CL.FUT")
    id_map = None
    if fut is not None and not fut.empty and "instrument_id" in fut.columns:
        m = fut.drop_duplicates("instrument_id").set_index("instrument_id")["symbol"].astype(str)
        id_map = {int(k): v for k, v in m.items() if dc.parse_future_symbol(v)}
    c0t = settlement_table(c0, "CL.c.0", id_map).rename(columns={"contract": "c0_contract", "settle": "nymex_c0"})
    # on a NYMEX last-trade day c.0 reports both the expiring and the new contract:
    # keep the earlier delivery month, which is the one c.0 was still mapped to
    c0t["_ord"] = c0t["c0_contract"].map(lambda c: (dc.parse_future_symbol(c) or {}).get("year", 0) * 100
                                         + (dc.parse_future_symbol(c) or {}).get("month", 0))
    c0t = c0t.sort_values(["settle_date", "_ord"]).drop_duplicates("settle_date", keep="first").drop(columns=["_ord"])
    futt = futt_raw.rename(columns={"contract": "cl_contract", "settle": "nymex_fm"})
    ltd = last_trade_dates(futt_raw)
    ev = ev.copy()
    j = ev.merge(c0t[["settle_date", "c0_contract", "nymex_c0"]], on="settle_date", how="left")
    j = j.merge(futt[["settle_date", "cl_contract", "nymex_fm"]], on=["settle_date", "cl_contract"], how="left")
    j["basis_c0"] = j["expiration_value"] - j["nymex_c0"]
    j["basis_fm"] = j["expiration_value"] - j["nymex_fm"]
    j["roll_mismatch"] = j["cl_contract"].notna() & j["c0_contract"].notna() & (j["cl_contract"] != j["c0_contract"])
    known = j["contract_rules"].notna() | j["contract_named"].notna()
    ref = j["contract_rules"].where(j["contract_rules"].notna(), j["contract_named"])
    j.attrs["calendar_agreement"] = (int((ref[known] == j.loc[known, "contract_calendar"]).sum()), int(known.sum()))
    j.attrs["ltd"] = {k: str(v) for k, v in ltd.items()}
    # evidence for every non-zero event: that day's settlement of the nearby contracts
    ev_rows = []
    j["assignment_ambiguous"] = False
    for idx, r in j[j["basis_fm"].notna() & (j["basis_fm"].abs() > 0.005)].iterrows():
        day = futt_raw[futt_raw["settle_date"] == r["settle_date"]]
        ordered = sorted(((dc.parse_future_symbol(c)["year"], dc.parse_future_symbol(c)["month"], c, v)
                          for c, v in zip(day["contract"], day["settle"]) if dc.parse_future_symbol(c)))
        names = [c for _, _, c, _ in ordered]
        pos = names.index(r["cl_contract"]) if r["cl_contract"] in names else 0
        near = ordered[max(0, pos - 1): pos + 3]
        match = [c for _, _, c, v in ordered if abs(v - r["expiration_value"]) < 0.005]
        ambiguous = bool(match) and r["front_month_source"] == "calendar"
        j.loc[idx, "assignment_ambiguous"] = ambiguous
        ev_rows.append({"settle_date": r["settle_date"], "series": r["series"], "kalshi": r["expiration_value"],
                        "contract": r["cl_contract"], "source": r["front_month_source"], "nymex": r["nymex_fm"],
                        "basis": r["basis_fm"], "matches_contract": ",".join(match) or "none",
                        "kind": "roll-boundary assignment" if ambiguous else "UNEXPLAINED",
                        "nearby": ", ".join("%s %.2f" % (c, v) for _, _, c, v in near)})
    j.attrs["nonzero"] = ev_rows
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
    agree, n_known = j.attrs.get("calendar_agreement", (0, 0))
    src = have["front_month_source"].value_counts().to_dict()
    L.append("Kalshi events with a settlement value: %d (%s). Joined to a NYMEX c.0 settlement: %d; to the "
             "reference contract: %d. Reference contract source: %s. Kalshi's calendar convention (next month from "
             "the 16th) reproduces the stated contract on %d of %d events where one is stated." % (
                 len(have), ", ".join("%s %d" % (s, n) for s, n in have["series"].value_counts().items()),
                 int(have["nymex_c0"].notna().sum()), int(have["nymex_fm"].notna().sum()),
                 ", ".join("%s %d" % kv for kv in src.items()), agree, n_known))
    L.append("")
    L.append("## Distribution of ICE - NYMEX ($/bbl), by series")
    L.append("")
    L.append("| series | basis | n | mean | median | sd | min | p5 | p95 | max | verdict |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    verdicts = {}
    amb = have["assignment_ambiguous"] if "assignment_ambiguous" in have.columns else (have["basis_fm"] != have["basis_fm"])
    unexplained = have[have["basis_fm"].notna() & (have["basis_fm"].abs() > 0.005) & ~amb]
    outliers = unexplained
    for s, g in have.groupby("series"):
        stated = g[g["front_month_source"].isin(["rules", "named"])]
        clean = g[~amb.reindex(g.index).fillna(False)]
        for col, label, sub in (("basis_fm", "vs reference contract (contract stated by Kalshi)", stated),
                                ("basis_fm", "vs reference contract (all events)", g),
                                ("basis_fm", "vs reference contract, roll-boundary assignments excluded", clean),
                                ("basis_c0", "vs CL.c.0 (contaminated by rolls)", g)):
            d = describe(sub[col])
            v = verdict(d)
            if label.startswith("vs reference contract, roll-boundary"):
                verdicts[(s, col)] = v
            if d["n"]:
                L.append("| %s | %s | %d | %+.3f | %+.3f | %.3f | %+.2f | %+.3f | %+.3f | %+.2f | %s |" % (
                    s, label, d["n"], d["mean"], d["median"], d["sd"], d["min"], d["p5"], d["p95"], d["max"], v))
            else:
                L.append("| %s | %s | 0 | - | - | - | - | - | - | - | %s |" % (s, label, v))
    exact = have[have["basis_fm"].notna()]
    if len(exact):
        L.append("")
        L.append("Events where ICE and NYMEX settled within $0.005 of each other: **%d of %d** (%.0f%%); within $0.05: %d." % (
            int((exact["basis_fm"].abs() < 0.005).sum()), len(exact), 100.0 * (exact["basis_fm"].abs() < 0.005).mean(),
            int((exact["basis_fm"].abs() < 0.05).sum())))
    L.append("")
    L.append("Verdict thresholds against a $1-wide bracket: **tight** = |mean| < 0.05, sd < 0.10, "
             "95th pct of |basis| < 0.25; **meaningful-but-stable** = |mean| < 0.15, sd < 0.30, "
             "95th pct < 0.60; else **too wide**.")
    L.append("")
    both = [v for (s, c), v in verdicts.items() if c == "basis_fm" and v != "insufficient data"]
    mechanical = ("too wide" if "too wide" in both else "meaningful-but-stable" if "meaningful-but-stable" in both
                  else "tight" if both else "insufficient data")
    nz = j.attrs.get("nonzero", [])
    n_amb = sum(1 for r in nz if r["kind"] != "UNEXPLAINED")
    n_out = len(outliers)
    clean = have[~amb]
    exact_share = float((clean["basis_fm"].abs() < 0.005).mean()) if len(clean) else 0.0
    big = outliers[outliers["basis_fm"].abs() > 1.0]
    if exact_share >= 0.95 and n_out <= max(3, int(0.03 * len(clean))):
        overall = "tight in the body, with a real tail"
        L.append("## Verdict: **%s**" % overall)
        L.append("")
        L.append("On %.0f%% of events (%d of %d, roll-boundary assignments excluded) Kalshi's ICE settlement equals "
                 "the NYMEX settlement to the cent: no persistent offset, no noise. The mechanical threshold verdict "
                 "on the same events is '%s' because of %d unexplained event%s, %d of which exceed a full $1 bracket "
                 "width. That is the tail the brief warned about: rare, unhedgeable by construction, and it must be "
                 "understood (Kalshi settlement anomaly, or a genuine ICE dislocation) before position size is "
                 "chosen. Sizing rule of thumb from this sample: one event per ~%d settlements where the ICE-NYMEX "
                 "difference reaches $%.2f." % (
                     100 * exact_share, int((clean["basis_fm"].abs() < 0.005).sum()), len(clean), mechanical,
                     n_out, "s" if n_out != 1 else "", len(big), max(1, len(clean) // max(1, len(big))),
                     float(big["basis_fm"].abs().max()) if len(big) else 0.0))
    else:
        overall = mechanical
        L.append("## Verdict: **%s**%s" % (
            overall, (" - %d unexplained event%s (listed below)" % (n_out, "s" if n_out != 1 else "")) if n_out else ""))
    L.append("")
    if nz:
        L.append("Every event where ICE and NYMEX did NOT settle within half a cent, with that day's NYMEX "
                 "settlements of the adjacent contract months. A `roll-boundary assignment` is an event in the "
                 "early 'front-month' era (no contract named in the rules) where Kalshi's value equals the "
                 "adjacent month to the cent: the calendar fallback assigned the wrong month, the exchanges "
                 "agreed. `UNEXPLAINED` matches no contract that day.")
        L.append("")
        L.append("| date | series | Kalshi (ICE) | reference | source | NYMEX | basis | Kalshi value matches | kind | adjacent NYMEX settlements |")
        L.append("|---|---|---:|---|---|---:|---:|---|---|---|")
        for r in nz:
            L.append("| %s | %s | %.2f | %s | %s | %.2f | %+.2f | %s | %s | %s |" % (
                r["settle_date"], r["series"], r["kalshi"], r["contract"], r["source"], r["nymex"], r["basis"],
                r["matches_contract"], r["kind"], r["nearby"]))
        L.append("")
        L.append("%d roll-boundary assignment%s, %d unexplained." % (n_amb, "s" if n_amb != 1 else "", n_out))
        L.append("")
    if overall.startswith("tight"):
        L.append("A NYMEX CL option is an adequate hedge for a Kalshi ICE-settled bracket on the current "
                 "account in the body of the distribution; no ICE licence is needed for the basis. The tail "
                 "events above are the residual risk to size against.")
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
    L.append("Dates where Databento's continuous CL.c.0 was on a different contract than Kalshi's reference "
             "contract: **%d of %d** comparable dates. Kalshi moves to the next delivery month on the 16th of each "
             "month, weeks before the NYMEX last trade; c.0 rolls the session after the last trade. Between those "
             "two dates the c.0 basis is the calendar spread, not an exchange difference. NYMEX last trade dates "
             "read from the data: %s." % (
                 len(mm), len(known), ", ".join("%s %s" % kv for kv in sorted(j.attrs.get("ltd", {}).items()))))
    if len(mm):
        L.append("")
        L.append("| date | series | Kalshi front month | CL.c.0 contract | basis vs c.0 | basis vs front month |")
        L.append("|---|---|---|---|---:|---:|")
        for r in mm.itertuples():
            L.append("| %s | %s | %s (%s) | %s | %s | %s |" % (
                r.settle_date, r.series, r.cl_contract, r.front_month_source[0] if isinstance(r.front_month_source, str) else "?", r.c0_contract,
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
    L.append("## Time series")
    L.append("")
    L.append("| date | series | ICE (Kalshi) | front month | NYMEX | basis | c.0 contract | NYMEX c.0 | basis c.0 |")
    L.append("|---|---|---:|---|---:|---:|---|---:|---:|")
    for r in have.sort_values("settle_ts").itertuples():
        f = lambda v, p="%.2f": (p % v) if v == v else "-"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r.settle_date, r.series, f(r.expiration_value),
            ("%s (%s)" % (r.cl_contract, (r.front_month_source or "?")[0])) if isinstance(r.cl_contract, str) else "-",
            f(r.nymex_fm), f(r.basis_fm, "%+.3f"), r.c0_contract if isinstance(r.c0_contract, str) else "-",
            f(r.nymex_c0), f(r.basis_c0, "%+.3f")))
    L.append("")
    L.append("## statistics schema contents (UNVERIFIED item 5, now measured)")
    L.append("")
    L.append("stat_type values seen on CL.c.0: %s. SETTLEMENT_PRICE = 3 carries the daily settlement, published "
             "about 14:30:50 ET and repeated (same price) at ~17:40 ET and again the next morning with "
             "stat_flags=3. `ts_ref` is midnight UTC of the trade date (20:00 ET the evening before): use its UTC "
             "date, never its ET date. The continuous symbol's `symbol` column is 'CL.c.0'; the contract is "
             "recovered from instrument_id via the CL.FUT records." % json.dumps(stats_types))
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
        ax.plot(g["settle_ts"], g["basis_fm"], marker="o", ms=3, lw=0.8, label="%s vs front month" % s)
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
    costs = {e["name"]: float(e["cost"]) for e in dbc.manifest.entries.values() if e.get("status") == "ok"}
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
