"""The half-spread of CL weekly option quotes, measured, by moneyness and by option price (Task B of
NightKing/HANDOFF_legcount_and_friction.md), and the availability of the legs the backtest needs.

Two sources, reported side by side:

  tbbo    every TBBO record (a BBO attached to a trade) in the 60 minutes before each backtest snapshot on the
          option expiry the backtest used - trade-sampled, so biased toward strikes that print
  bbo1m   the bbo-1m quotes of the same windows (data_cme/parquet/options_bbo_1m, the whole parent chain, filtered to
          the expiry the backtest used): one sample per instrument per minute whether or not it traded

Bins: distance from the snapshot forward in dollars, in vol-scales (|K - F0| / (F0 sigma sqrt(T)) with the chain's ATM
sigma), and the option's own premium. Leg availability: for every bracket of every window, each replicating leg
(the structure_spec strikes, OTM side) - was it two-sided at the snapshot minute on bbo-1m, and on the TBBO within
5 and within 60 minutes?

    python3 -m synth.friction_measure            # writes synth/results_backtest/friction_measure.json and prints the tables
"""

from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_CME = ROOT / "data_cme" / "parquet"
BBO_DIR = DATA_CME / "options_bbo_1m"
OUT = HERE / "results_backtest" / "friction_measure.json"
ET = "America/New_York"
WINDOW_MIN = 60
BBO_MAX_AGE_MIN = 2.0
DOLLAR_BANDS = [("<0.5", 0.0, 0.5), ("0.5-1", 0.5, 1.0), ("1-2", 1.0, 2.0), ("2-3", 2.0, 3.0), ("3-4", 3.0, 4.0), ("4-6", 4.0, 6.0), ("6-8", 6.0, 8.0), ("8-12", 8.0, 12.0), (">12", 12.0, 1e9)]
VOL_BANDS = [("<0.25", 0.0, 0.25), ("0.25-0.5", 0.25, 0.5), ("0.5-1", 0.5, 1.0), ("1-1.5", 1.0, 1.5), ("1.5-2", 1.5, 2.0), ("2-3", 2.0, 3.0), ("3-4", 3.0, 4.0), (">4", 4.0, 1e9)]
PRICE_BANDS = [("<0.05", 0.0, 0.05), ("0.05-0.10", 0.05, 0.10), ("0.10-0.25", 0.10, 0.25), ("0.25-0.50", 0.25, 0.50), ("0.50-1", 0.50, 1.0), ("1-2", 1.0, 2.0), (">2", 2.0, 1e9)]


def windows(series: str = "KXWTIW") -> List[Dict[str, Any]]:
    rs = pickle.load(open(HERE / "results_backtest" / ("runs_%s.pkl" % series), "rb"))
    out = []
    for r in rs:
        if r["outcome"] not in ("cleared", "g4_split_half_fired", "sampler_fail") or not r.get("snap_time_et"):
            continue
        x = r["extraction"]
        out.append({"date": r["settle_date"], "snap": r["snap"], "root": r["root"], "snap_time_et": r["snap_time_et"], "F0": r["F0"],
                    "vs": max(x["atm_sigma"], 0.05) * np.sqrt(max(x["T_years"], 1e-6)) * r["F0"],   # one vol-scale in dollars
                    "brackets": [(b["lo"], b["hi"], b.get("status"), b.get("kalshi_mid") is not None) for b in r["brackets"]]})
    return sorted(out, key=lambda w: (w["date"], w["snap"]))


_DEFS: Dict[str, Any] = {}


def expiry_symbols(root: str, settle_date: str) -> set:
    """Raw symbols of the options expiring on the settlement date (the backtest's chain)."""
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    import db_pull
    if root not in _DEFS:
        files = sorted((DATA_CME / "options_definition" / ("root=%s" % root)).glob("*.parquet"))
        _DEFS[root] = db_pull.parse_definitions(pd.concat([pd.read_parquet(f) for f in files], ignore_index=True), root)
    d = _DEFS[root]
    d = d[d["expiry_date"].astype(str) == settle_date]
    col = "raw_symbol" if "raw_symbol" in d.columns else "symbol"
    return set(d[col].astype(str))


def _decorate(e, w):
    e["hs"] = 0.5 * (e["ask_px_00"] - e["bid_px_00"])
    e["mid"] = 0.5 * (e["ask_px_00"] + e["bid_px_00"])
    e["m"] = (e["strike"] - w["F0"]).abs()
    e["mv"] = e["m"] / w["vs"]
    e["otm"] = np.where(e["right"] == "C", e["strike"] >= w["F0"], e["strike"] < w["F0"])
    e["window"] = "%s %s" % (w["date"], w["snap"])
    return e


def tbbo_events(w: Dict[str, Any]):
    import pandas as pd
    p = DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % w["root"]) / ("expiry=%s" % w["date"]) / "part.parquet"
    tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
    t1 = pd.Timestamp(w["snap_time_et"]).tz_localize(ET).tz_convert("UTC")
    t0 = t1 - pd.Timedelta(minutes=WINDOW_MIN)
    e = tb[(tb["ts_event"] > t0) & (tb["ts_event"] <= t1) & tb["bid_px_00"].notna() & tb["ask_px_00"].notna() & (tb["bid_px_00"] > 0) & (tb["ask_px_00"] > tb["bid_px_00"])].copy()
    e["age_min"] = (t1 - e["ts_event"]).dt.total_seconds() / 60.0
    return _decorate(e, w)


def bbo1m_snapshot(w: Dict[str, Any], max_age_min: float = BBO_MAX_AGE_MIN):
    """The bbo-1m sample of each instrument of the backtest's expiry nearest before the snapshot (<= max_age_min old),
    two-sided only; None if the window is not on disk."""
    import pandas as pd
    p = BBO_DIR / ("date=%s" % w["date"]) / ("snap=%s" % w["snap"]) / "part.parquet"
    if not p.exists():
        return None
    q = pd.read_parquet(p)
    if "strike" not in q.columns:
        sys.path.insert(0, str(ROOT))
        import db_common as dc
        pr = q["symbol"].map(lambda x: dc.parse_option_symbol(str(x)) or {})
        q["strike"] = pr.map(lambda t: t.get("strike"))
        q["right"] = pr.map(lambda t: t.get("right"))
    syms = expiry_symbols(w["root"], w["date"])
    q = q[q["symbol"].astype(str).isin(syms)].copy()
    # bbo-1m: ts_recv is the sample time (the minute boundary at which the book was read); ts_event is the time of the
    # last book update behind that BBO, which can be hours earlier for a resting quote
    q["ts_recv"] = pd.to_datetime(q["ts_recv"], utc=True)
    q["ts_event"] = pd.to_datetime(q["ts_event"], utc=True)
    t1 = pd.Timestamp(w["snap_time_et"]).tz_localize(ET).tz_convert("UTC")
    q = q[q["ts_recv"] <= t1].sort_values("ts_recv").groupby("symbol").tail(1).copy()
    q["age_min"] = (t1 - q["ts_recv"]).dt.total_seconds() / 60.0
    q["quote_age_min"] = (t1 - q["ts_event"]).dt.total_seconds() / 60.0
    q = q[q["age_min"] <= max_age_min]
    q["n_all"] = len(q)
    q = q[q["bid_px_00"].notna() & q["ask_px_00"].notna() & (q["bid_px_00"] > 0) & (q["ask_px_00"] > q["bid_px_00"])].copy()
    return _decorate(q, w)


def bbo1m_all(w: Dict[str, Any]):
    """Every bbo-1m sample of the window (for the distribution tables), two-sided only."""
    import pandas as pd
    p = BBO_DIR / ("date=%s" % w["date"]) / ("snap=%s" % w["snap"]) / "part.parquet"
    if not p.exists():
        return None
    q = pd.read_parquet(p)
    if "strike" not in q.columns:
        sys.path.insert(0, str(ROOT))
        import db_common as dc
        pr = q["symbol"].map(lambda x: dc.parse_option_symbol(str(x)) or {})
        q["strike"] = pr.map(lambda t: t.get("strike"))
        q["right"] = pr.map(lambda t: t.get("right"))
    syms = expiry_symbols(w["root"], w["date"])
    q = q[q["symbol"].astype(str).isin(syms)]
    q = q[q["bid_px_00"].notna() & q["ask_px_00"].notna() & (q["bid_px_00"] > 0) & (q["ask_px_00"] > q["bid_px_00"])].copy()
    return _decorate(q, w)


def _bands(d, col, bands):
    rows = []
    for name, lo, hi in bands:
        s = d[(d[col] >= lo) & (d[col] < hi)]["hs"]
        if len(s):
            rows.append({"band": name, "n": int(len(s)), "p25": float(100 * s.quantile(0.25)), "median": float(100 * s.median()), "p75": float(100 * s.quantile(0.75)),
                         "mean": float(100 * s.mean()), "share_le_1c": float((s <= 0.0101).mean()), "share_le_2c": float((s <= 0.0201).mean()),
                         "n_windows": int(d[(d[col] >= lo) & (d[col] < hi)]["window"].nunique())})
    return rows


def summarise(frames, label: str) -> Dict[str, Any]:
    import pandas as pd
    if not frames:
        return {"label": label, "n": 0}
    d = pd.concat(frames, ignore_index=True)
    d = d[d["otm"]]
    out: Dict[str, Any] = {"label": label, "n": int(len(d)), "windows": int(d["window"].nunique())}
    out["by_dollars"] = _bands(d, "m", DOLLAR_BANDS)
    out["by_volscale"] = _bands(d, "mv", VOL_BANDS)
    out["by_price"] = _bands(d, "mid", PRICE_BANDS)
    return out


def leg_availability(ws, tb_last: Dict[str, Any], bbo_snap: Dict[str, Any]) -> Dict[str, Any]:
    """For every bracket of every window: its replicating legs (OTM side), and whether each was two-sided on the TBBO
    within 5 / 60 minutes and on bbo-1m at the snapshot minute; binned by the leg's distance from the forward."""
    from . import backtest as bt
    rows = []
    for w in ws:
        key = "%s %s" % (w["date"], w["snap"])
        tb = tb_last.get(key)
        bb = bbo_snap.get(key)
        for lo, hi, status, two_sided in w["brackets"]:
            spec = bt.structure_spec(lo, hi)
            legs_ok = {"tbbo5": True, "tbbo60": True, "bbo1m": True}
            for k, _ in spec["legs"]:
                right = "C" if k >= w["F0"] else "P"
                m = abs(k - w["F0"])
                row = {"window": key, "status": status, "two_sided_kalshi": two_sided, "strike": k, "m": m, "mv": m / w["vs"], "n_legs": len(spec["legs"])}
                for src, df, maxage in (("tbbo5", tb, 5.0), ("tbbo60", tb, 60.0)):
                    ok = False
                    if df is not None and len(df):
                        sel = df[(np.isclose(df["strike"].values, k)) & (df["age_min"] <= maxage)]
                        ok = bool(len(sel))
                    row[src] = ok
                    legs_ok[src] &= ok
                ok = False
                hs = None
                if bb is not None and len(bb):
                    sel = bb[np.isclose(bb["strike"].values, k) & (bb["right"].values == right)]
                    if sel.empty:
                        sel = bb[np.isclose(bb["strike"].values, k)]
                    ok = bool(len(sel))
                    hs = float(sel["hs"].iloc[0]) if ok else None
                row["bbo1m"] = ok
                row["bbo1m_hs"] = hs
                row["bbo1m_on_disk"] = bb is not None
                rows.append(row)
            rows[-1]["bracket_all_legs"] = dict(legs_ok)
    import pandas as pd
    d = pd.DataFrame(rows)
    out: Dict[str, Any] = {"n_legs": int(len(d)), "n_windows_with_bbo": int(d[d["bbo1m_on_disk"]]["window"].nunique())}
    tab = []
    for name, lo, hi in DOLLAR_BANDS:
        s = d[(d["m"] >= lo) & (d["m"] < hi)]
        if len(s):
            sb = s[s["bbo1m_on_disk"]]
            tab.append({"band": name, "n": int(len(s)), "tbbo5": float(s["tbbo5"].mean()), "tbbo60": float(s["tbbo60"].mean()),
                        "bbo1m": float(sb["bbo1m"].mean()) if len(sb) else None, "n_bbo": int(len(sb)),
                        "bbo1m_hs_median": float(100 * sb["bbo1m_hs"].dropna().median()) if sb["bbo1m_hs"].notna().any() else None})
    out["by_dollars"] = tab
    # brackets the TBBO dropped as cme_leg_unquoted: were all their legs live on bbo-1m?
    br = d.dropna(subset=["bracket_all_legs"]) if "bracket_all_legs" in d.columns else d.iloc[0:0]
    unq = br[(br["status"] == "cme_leg_unquoted") & br["bbo1m_on_disk"]]
    out["tbbo_unquoted_brackets"] = {"n": int(len(unq)), "all_legs_live_on_bbo1m": int(sum(1 for v in unq["bracket_all_legs"] if v["bbo1m"])),
                                     "all_legs_tbbo60": int(sum(1 for v in unq["bracket_all_legs"] if v["tbbo60"]))}
    comp = br[br["two_sided_kalshi"] & br["bbo1m_on_disk"]]
    out["two_sided_brackets"] = {"n": int(len(comp)), "all_legs_bbo1m": int(sum(1 for v in comp["bracket_all_legs"] if v["bbo1m"])),
                                 "all_legs_tbbo5": int(sum(1 for v in comp["bracket_all_legs"] if v["tbbo5"])), "all_legs_tbbo60": int(sum(1 for v in comp["bracket_all_legs"] if v["tbbo60"]))}
    return out


def table(rows: List[Dict[str, Any]]) -> str:
    L = ["| band | n | windows | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        L.append("| %s | %d | %d | %.2f | %.2f | %.2f | %.2f | %.0f%% | %.0f%% |" % (r["band"], r["n"], r["n_windows"], r["p25"], r["median"], r["p75"], r["mean"], 100 * r["share_le_1c"], 100 * r["share_le_2c"]))
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    ws = windows()
    tb_frames, bbo_frames = [], []
    tb_last: Dict[str, Any] = {}
    bbo_snap: Dict[str, Any] = {}
    for w in ws:
        key = "%s %s" % (w["date"], w["snap"])
        e = tbbo_events(w)
        tb_frames.append(e)
        tb_last[key] = e.sort_values("ts_event").groupby("instrument_id").tail(1)
        q = bbo1m_all(w)
        if q is not None:
            bbo_frames.append(q)
            bbo_snap[key] = bbo1m_snapshot(w)
    S = {"tbbo": summarise(tb_frames, "TBBO events in the 60-minute window (trade-sampled)"),
         "bbo1m": summarise(bbo_frames, "bbo-1m samples in the 60-minute window (every minute, every instrument of the expiry)"),
         "bbo1m_snapshot": summarise([v for v in bbo_snap.values() if v is not None], "bbo-1m at the snapshot minute (one quote per instrument)"),
         "legs": leg_availability(ws, tb_last, bbo_snap), "n_windows": len(ws), "n_windows_bbo": len(bbo_frames)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(S, open(OUT, "w"), indent=1)
    for k in ("tbbo", "bbo1m", "bbo1m_snapshot"):
        s = S[k]
        print("\n== %s: n %d" % (s["label"], s["n"]))
        if s["n"]:
            print("by |K - F0| ($):\n" + table(s["by_dollars"]))
            print("by |K - F0| in vol-scales:\n" + table(s["by_volscale"]))
            print("by option mid ($/bbl):\n" + table(s["by_price"]))
    lg = S["legs"]
    print("\n== leg availability (every replicating leg of every bracket, %d legs, bbo-1m on disk for %d windows)" % (lg["n_legs"], lg["n_windows_with_bbo"]))
    print("| band | legs | two-sided TBBO ≤ 5 min | TBBO ≤ 60 min | bbo-1m at the minute | bbo-1m half-spread median |")
    for r in lg["by_dollars"]:
        print("| %s | %d | %.0f%% | %.0f%% | %s | %s |" % (r["band"], r["n"], 100 * r["tbbo5"], 100 * r["tbbo60"], ("%.0f%%" % (100 * r["bbo1m"])) if r["bbo1m"] is not None else "—",
                                                       ("%.2f¢" % r["bbo1m_hs_median"]) if r["bbo1m_hs_median"] is not None else "—"))
    print("TBBO-unquoted brackets:", lg["tbbo_unquoted_brackets"], "two-sided brackets:", lg["two_sided_brackets"])
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
