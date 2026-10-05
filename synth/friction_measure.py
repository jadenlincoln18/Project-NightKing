"""The half-spread of CL weekly option quotes, measured, by moneyness and by option price (Task B of
NightKing/HANDOFF_legcount_and_friction.md).

Two sources, reported side by side:

  tbbo    every TBBO record (a BBO attached to a trade) in the 60 minutes before each backtest snapshot on the
          option expiry the backtest used - trade-sampled, so biased toward strikes that print
  bbo1m   the bbo-1m quotes of the same windows if the scoped pull has been made (data_cme/parquet/options_bbo_1m);
          one quote per instrument per minute whether or not it traded - the proper measurement

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
MONEY_BANDS = [("<0.5", 0.0, 0.5), ("0.5-1", 0.5, 1.0), ("1-2", 1.0, 2.0), ("2-4", 2.0, 4.0), ("4-8", 4.0, 8.0)]
PRICE_BANDS = [("<0.10", 0.0, 0.10), ("0.10-0.25", 0.10, 0.25), ("0.25-0.50", 0.25, 0.50), ("0.50-1", 0.50, 1.0), ("1-2", 1.0, 2.0), (">2", 2.0, 1e9)]


def windows(series: str = "KXWTIW") -> List[Dict[str, Any]]:
    rs = pickle.load(open(HERE / "results_backtest" / ("runs_%s.pkl" % series), "rb"))
    out = []
    for r in rs:
        if r["outcome"] not in ("cleared", "g4_split_half_fired", "sampler_fail") or not r.get("snap_time_et"):
            continue
        out.append({"date": r["settle_date"], "snap": r["snap"], "root": r["root"], "snap_time_et": r["snap_time_et"], "F0": r["F0"]})
    return sorted(out, key=lambda w: (w["date"], w["snap"]))


def tbbo_events(w: Dict[str, Any]):
    import pandas as pd
    p = DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % w["root"]) / ("expiry=%s" % w["date"]) / "part.parquet"
    tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
    t1 = pd.Timestamp(w["snap_time_et"]).tz_localize(ET).tz_convert("UTC")
    t0 = t1 - pd.Timedelta(minutes=WINDOW_MIN)
    e = tb[(tb["ts_event"] > t0) & (tb["ts_event"] <= t1) & tb["bid_px_00"].notna() & tb["ask_px_00"].notna() & (tb["bid_px_00"] > 0) & (tb["ask_px_00"] > tb["bid_px_00"])].copy()
    e["hs"] = 0.5 * (e["ask_px_00"] - e["bid_px_00"])
    e["mid"] = 0.5 * (e["ask_px_00"] + e["bid_px_00"])
    e["m"] = (e["strike"] - w["F0"]).abs()
    e["otm"] = np.where(e["right"] == "C", e["strike"] >= w["F0"], e["strike"] < w["F0"])
    e["age_min"] = (t1 - e["ts_event"]).dt.total_seconds() / 60.0
    return e


def bbo1m_quotes(w: Dict[str, Any]):
    """bbo-1m rows for the window if on disk (one file per window, written by db_pull_bbo.py); None otherwise."""
    import pandas as pd
    p = BBO_DIR / ("date=%s" % w["date"]) / ("snap=%s" % w["snap"]) / "part.parquet"
    if not p.exists():
        return None
    q = pd.read_parquet(p)
    q = q[q["bid_px_00"].notna() & q["ask_px_00"].notna() & (q["bid_px_00"] > 0) & (q["ask_px_00"] > q["bid_px_00"])].copy()
    q["hs"] = 0.5 * (q["ask_px_00"] - q["bid_px_00"])
    q["mid"] = 0.5 * (q["ask_px_00"] + q["bid_px_00"])
    q["m"] = (q["strike"] - w["F0"]).abs()
    q["otm"] = np.where(q["right"] == "C", q["strike"] >= w["F0"], q["strike"] < w["F0"])
    return q


def summarise(frames, label: str) -> Dict[str, Any]:
    import pandas as pd
    if not frames:
        return {"label": label, "n": 0}
    d = pd.concat(frames, ignore_index=True)
    d = d[d["otm"]]
    out: Dict[str, Any] = {"label": label, "n": int(len(d)), "windows": int(d["window"].nunique())}
    rows = []
    for name, lo, hi in MONEY_BANDS:
        s = d[(d["m"] >= lo) & (d["m"] < hi)]["hs"]
        if len(s):
            rows.append({"band": name, "n": int(len(s)), "p25": float(100 * s.quantile(0.25)), "median": float(100 * s.median()), "p75": float(100 * s.quantile(0.75)),
                         "mean": float(100 * s.mean()), "share_le_1c": float((s <= 0.0101).mean()), "share_le_2c": float((s <= 0.0201).mean())})
    out["by_moneyness"] = rows
    rows = []
    for name, lo, hi in PRICE_BANDS:
        s = d[(d["mid"] >= lo) & (d["mid"] < hi)]["hs"]
        if len(s):
            rows.append({"band": name, "n": int(len(s)), "p25": float(100 * s.quantile(0.25)), "median": float(100 * s.median()), "p75": float(100 * s.quantile(0.75)),
                         "mean": float(100 * s.mean()), "share_le_1c": float((s <= 0.0101).mean()), "share_le_2c": float((s <= 0.0201).mean())})
    out["by_price"] = rows
    # the legs the backtest would trade: strikes within $2 of the edges it priced, i.e. |K - F0| in the 0.5-4 range mostly
    legs = d[(d["m"] >= 0.5) & (d["m"] < 4.0)]["hs"]
    out["leg_region"] = {"n": int(len(legs)), "median": float(100 * legs.median()) if len(legs) else None, "p75": float(100 * legs.quantile(0.75)) if len(legs) else None,
                         "mean": float(100 * legs.mean()) if len(legs) else None}
    return out


def table(S: Dict[str, Any], key: str) -> str:
    L = ["| band | n | p25 | median | p75 | mean | ≤ 1¢ | ≤ 2¢ |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in S.get(key, []):
        L.append("| %s | %d | %.2f | %.2f | %.2f | %.2f | %.0f%% | %.0f%% |" % (r["band"], r["n"], r["p25"], r["median"], r["p75"], r["mean"], 100 * r["share_le_1c"], 100 * r["share_le_2c"]))
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    ws = windows()
    tb_frames, bbo_frames = [], []
    fresh = []
    for w in ws:
        e = tbbo_events(w)
        e["window"] = "%s %s" % (w["date"], w["snap"])
        tb_frames.append(e)
        last = e.sort_values("ts_event").groupby("instrument_id").tail(1)
        fresh.append({"window": e["window"].iloc[0] if len(e) else None, "n_events": int(len(e)), "n_instruments": int(last["instrument_id"].nunique()),
                      "n_fresh_5min": int((last["age_min"] <= 5).sum()), "n_within_4_of_F0": int((last["m"] <= 4).sum()), "n_fresh_within_4": int(((last["age_min"] <= 5) & (last["m"] <= 4)).sum())})
        q = bbo1m_quotes(w)
        if q is not None:
            q["window"] = "%s %s" % (w["date"], w["snap"])
            bbo_frames.append(q)
    S = {"tbbo": summarise(tb_frames, "TBBO events in the 60-minute window (trade-sampled)"),
         "bbo1m": summarise(bbo_frames, "bbo-1m quotes in the 60-minute window (every minute, every instrument)"),
         "freshness": fresh, "n_windows": len(ws)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(S, open(OUT, "w"), indent=1)
    for k in ("tbbo", "bbo1m"):
        s = S[k]
        print("\n== %s: n %d" % (s["label"], s["n"]))
        if s["n"]:
            print("by |K - F0| ($):\n" + table(s, "by_moneyness"))
            print("by option mid ($/bbl):\n" + table(s, "by_price"))
            print("leg region (0.5-4 from the forward): median %.2fc, p75 %.2fc, mean %.2fc (n %d)" % (s["leg_region"]["median"], s["leg_region"]["p75"], s["leg_region"]["mean"], s["leg_region"]["n"]))
    f = fresh
    print("\nfreshness per window (TBBO): instruments quoted in the hour median %d, within $4 of F0 median %d, of which fresh (<= 5 min) median %d" % (
        np.median([x["n_instruments"] for x in f]), np.median([x["n_within_4_of_F0"] for x in f]), np.median([x["n_fresh_within_4"] for x in f])))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
