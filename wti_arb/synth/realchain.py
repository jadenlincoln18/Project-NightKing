"""Step 2: the extractor on real KXWTIW chains, descriptively only.

No Kalshi prices are read, no gap is computed, nothing is evaluated as a trade. For
every KXWTIW settlement date that clears Gate 0 (same-day weekly expiry, >= 8 strikes
with 3+ per wing in the final hour — `data_cme/parquet/chain_density`) the chain is
snapshotted at four times, and the full pipeline (Stage 6 -> Act II -> Act III with and
without the martingale constraint -> Gate 4 detector) is run on the three with time
left on the clock:

    T-2d   14:30 ET two business days before settlement
    T-1d   14:30 ET one business day before
    T-4h   10:30 ET on settlement day
    T-0    14:30 ET on settlement day: parity forward only (the chain is at intrinsic)

The 14:30 snapshots coincide with the NYMEX settlement window, so Stage 6's parity
forward is compared with the CME settlement of the option's own underlying contract
that day — the independent check the synthetic study could not provide.

    python3 -m synth.realchain                 # run (resumable), then report
    python3 -m synth.realchain --report        # re-render from what is on disk
    python3 -m synth.realchain --only 2026-03-13 --snap T-1d
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_CME = ROOT / "data_cme" / "parquet"
RESULTS = HERE / "results_real"
PLOTS = HERE / "plots_real"
ET = "America/New_York"
FRESH_MIN = 60
SNAPS = ("T-2d", "T-1d", "T-4h", "T-0")
NUTS = {"n_chains": 4, "n_warmup": 400, "n_samples": 400}
SERIES = "KXWTIW"
WINDOWS = (60, 10)   # minutes: Gate 0's own window, and a near-synchronous one (the underlying moves)
RATE = 0.04          # D = exp(-r T): at T <= 2 days the chain cannot identify D (it returned 0.947 at T-0)


# --------------------------------------------------------------------------
# inputs from the local stores (read-only)
# --------------------------------------------------------------------------

def load_inputs() -> Dict[str, Any]:
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    import db_common as dc
    import db_pull
    ev = dc.kalshi_settlements(series=(SERIES,))
    cd = pd.read_parquet(DATA_CME / "chain_density" / "part.parquet")
    cd = cd[(cd["series"] == SERIES) & (cd["clears"])]
    dates = []
    for r in cd.itertuples():
        e = ev[ev["settle_date"] == r.settle_date]
        if e.empty:
            continue
        e = e.iloc[0]
        dates.append({"settle_date": str(r.settle_date), "root": r.root, "settle_ts": e["settle_ts"],
                      "event_ticker": e["event_ticker"], "cl_contract": e["cl_contract"],
                      "ice_settle": float(e["expiration_value"]) if e["expiration_value"] == e["expiration_value"] else None,
                      "strikes_60m_settle": int(r.strikes_60m)})
    # option definitions: the underlying contract of each (root, expiry)
    under: Dict[Tuple[str, str], str] = {}
    for root in sorted({d["root"] for d in dates}):
        files = sorted((DATA_CME / "options_definition" / ("root=%s" % root)).glob("*.parquet"))
        if not files:
            continue
        defs = db_pull.parse_definitions(pd.concat([pd.read_parquet(f) for f in files], ignore_index=True), root)
        if "underlying" not in defs.columns:
            continue
        for exp_date, grp in defs.groupby("expiry_date"):
            under[(root, str(exp_date))] = str(grp["underlying"].mode().iloc[0])
    # NYMEX settlements by (trade date, contract)
    fs = pd.read_parquet(DATA_CME / "futures_stats" / "symbol=CL.FUT" / "part.parquet", columns=["ts_ref", "symbol", "price", "stat_type"])
    fs = fs[fs["stat_type"] == 3].dropna(subset=["ts_ref"])
    fs["date"] = pd.to_datetime(fs["ts_ref"], utc=True).dt.date.astype(str)
    settles = {(r.date, r.symbol): float(r.price) for r in fs.sort_values("ts_ref").itertuples()}
    return {"dates": dates, "underlying": under, "settles": settles}


def snapshot_times(settle_ts) -> Dict[str, Any]:
    import pandas as pd
    s = pd.Timestamp(settle_ts).tz_convert(ET)
    day = s.normalize()
    return {
        "T-2d": (s - pd.tseries.offsets.BDay(2)),
        "T-1d": (s - pd.tseries.offsets.BDay(1)),
        "T-4h": day + pd.Timedelta(hours=10, minutes=30),
        "T-0": s,
    }


def snapshot(tb, snap_ts, window_min: int = FRESH_MIN):
    """Last quote per instrument in the trailing window with a real two-sided market."""
    import pandas as pd
    w = tb[(tb["ts_event"] <= snap_ts) & (tb["ts_event"] > snap_ts - pd.Timedelta(minutes=window_min))]
    if w.empty:
        return None
    last = w.sort_values("ts_event").groupby("instrument_id").tail(1).copy()
    last = last[last["bid_px_00"].notna() & last["ask_px_00"].notna() & (last["bid_px_00"] > 0)
                & (last["ask_px_00"] > last["bid_px_00"])]
    if last.empty:
        return None
    last["mid"] = 0.5 * (last["bid_px_00"] + last["ask_px_00"])
    last["hs"] = 0.5 * (last["ask_px_00"] - last["bid_px_00"])
    last["age_min"] = (snap_ts - last["ts_event"]).dt.total_seconds() / 60.0
    return last.sort_values(["strike", "right"])


# --------------------------------------------------------------------------
# one (date, snapshot)
# --------------------------------------------------------------------------

def run_one(job: Dict[str, Any]) -> Dict[str, Any]:
    import pandas as pd
    from . import act2, act3, densities, detector, geometry, harness, stage6
    d, label, window = job["date"], job["snap"], int(job.get("window", 60))
    out: Dict[str, Any] = {"settle_date": d["settle_date"], "root": d["root"], "snap": label, "window_min": window,
                           "event_ticker": d["event_ticker"], "cl_contract_kalshi": d["cl_contract"], "ice_settle": d["ice_settle"],
                           "error": None}
    t0 = time.time()
    try:
        p = DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % d["root"]) / ("expiry=%s" % d["settle_date"]) / "part.parquet"
        tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
        times = snapshot_times(d["settle_ts"])
        snap_ts = times[label]
        out["snap_time_et"] = snap_ts.strftime("%Y-%m-%d %H:%M")
        T = max((pd.Timestamp(d["settle_ts"]) - snap_ts.tz_convert("UTC")).total_seconds() / (365.0 * 86400.0), 0.0)
        out["T_years"] = T
        q = snapshot(tb, snap_ts.tz_convert("UTC"), window)
        D_fixed = float(np.exp(-RATE * T))
        if q is None:
            out["gate0"] = False
            out["gate0_reason"] = "no two-sided quotes in the window"
            return out
        out["n_quoted_strikes"] = int(q["strike"].nunique())  # Gate 0's own count: any side, any strike
        out["gate0_pooled"] = bool(out["n_quoted_strikes"] >= 8)
        # Stage 6 on strikes with both sides
        piv = q.pivot_table(index="strike", columns="right", values=["mid", "hs", "age_min"])
        both = piv.dropna(subset=[("mid", "C"), ("mid", "P")]) if ("mid", "C") in piv.columns and ("mid", "P") in piv.columns else piv.iloc[0:0]
        st6 = None
        if len(both) >= 2:
            wts = 1.0 / (both[("hs", "C")].values ** 2 + both[("hs", "P")].values ** 2)
            st6 = stage6.parity_forward(both.index.values, both[("mid", "C")].values, both[("mid", "P")].values, weights=wts, fixed_D=D_fixed)
            st6_free = stage6.parity_forward(both.index.values, both[("mid", "C")].values, both[("mid", "P")].values, weights=wts) if len(both) >= 3 else None
            out["D_chain"] = float(st6_free["D"]) if st6_free and st6_free["ok"] else None
            out["F0_parity_freeD"] = float(st6_free["F0"]) if st6_free and st6_free["ok"] else None
        if st6 is None or not st6["ok"] or not np.isfinite(st6["F0"]):
            out["gate0"] = False
            out["gate0_reason"] = "fewer than 2 two-sided strikes for parity"
            return out
        F0, D, se = float(st6["F0"]), D_fixed, float(st6["se_F0"])
        if len(both) < 3:
            se = max(se, 0.10)  # two pairs: no residual degrees of freedom; a nominal 10c
        out.update({"F0_parity": F0, "se_F0": se, "D_used": D, "parity_pairs": int(st6["n_pairs"]), "parity_flagged": int(st6["flagged"].sum()),
                    "parity_resid_sd": float(st6["resid_sd"]), "two_sided_strikes": int(len(both))})
        # independent forward checks
        under = job["underlying"].get((d["root"], d["settle_date"]))
        out["underlying"] = under
        out["contract_month_match"] = (under == d["cl_contract"]) if under else None
        snap_date = snap_ts.strftime("%Y-%m-%d")
        nymex = job["settles"].get((snap_date, under)) if under else None
        out["nymex_settle_same_day"] = nymex
        if nymex is not None and label in ("T-2d", "T-1d", "T-0"):
            out["parity_minus_nymex_cents"] = 100.0 * (F0 - nymex)
        if label == "T-0" and d["ice_settle"] is not None:
            out["parity_minus_ice_cents"] = 100.0 * (F0 - d["ice_settle"])
        # OTM chain
        otm = q[np.where(q["right"] == "C", q["strike"] >= F0, q["strike"] < F0)]
        otm = otm.sort_values(["strike", "hs"]).drop_duplicates("strike", keep="first")
        K = otm["strike"].values.astype(float)
        R = otm["right"].values
        mid = otm["mid"].values.astype(float)
        hs = otm["hs"].values.astype(float)
        n_below, n_above = int((K < F0).sum()), int((K >= F0).sum())
        out.update({"n_strikes": int(len(K)), "n_below": n_below, "n_above": n_above,
                    "quote_age_median_min": float(otm["age_min"].median()), "frac_at_floor": float(np.mean(hs <= 0.005 + 1e-9)),
                    "frac_bid_1c": float(np.mean(otm["bid_px_00"].values <= 0.0101)), "hs_median": float(np.median(hs)),
                    "K": K, "right": R, "mid": mid, "hs": hs})
        geo = geometry.load()
        m = geo["half_spread_model"]
        pred = np.exp(m["alpha"] + m["beta"] * np.log(np.maximum(mid, m["floor"])))
        out["hs_log_ratio_to_model_median"] = float(np.median(np.log(np.maximum(hs, 0.0025) / pred)))
        out["gate0"] = bool(len(K) >= 8 and n_below >= 3 and n_above >= 3)
        if not out["gate0"]:
            out["gate0_reason"] = "%d strikes, %d/%d per wing" % (len(K), n_below, n_above)
            return out
        if label == "T-0":
            return out  # parity only at expiry
        edges = densities.kalshi_edges(F0)
        out["edges"] = edges
        # Act II
        try:
            a2 = act2.run(K, R, mid, hs, F0, D, T, edges, rng=np.random.default_rng(0))
        except Exception as exc:
            a2 = {"ok": False, "reason": repr(exc)}
        out["act2_ok"] = bool(a2.get("ok"))
        if a2.get("ok"):
            out["act2_bracket"] = a2["bracket_probs"]
            out["act2_checks"] = a2["checks"]
            out["act2_svi"] = {k: float(v) if isinstance(v, (float, int, np.floating, np.bool_)) else v for k, v in a2["svi"].items()}
            out["act2_grid"] = (a2["grid"], a2["density"])
            out["act2_n_used"] = a2["n_used"]
            out["act2_n_dropped"] = a2["n_dropped"]
        else:
            out["act2_reason"] = a2.get("reason")
        # Act III, constrained then unconstrained
        asig = act3.atm_sigma(K, R, mid, F0, D, T)
        out["atm_sigma"] = asig
        for mart, tag in ((True, "act3"), (False, "act3u")):
            model = act3.Model(K, R, mid, hs, F0, D, T, asig, se_F0=se, martingale=mart)
            rng = np.random.default_rng(1 if mart else 2)
            res = act3.sample(model, rng, sampler="nuts", **NUTS)
            summ = model.summarise(res["thetas"], edges)
            br = summ["bracket"]
            n_ch = NUTS["n_chains"]
            chains_br = br.reshape(n_ch, -1, br.shape[1])
            keep = chains_br.std(axis=(0, 1)) > 1e-12
            sub = res["thetas"][:: max(1, len(res["thetas"]) // 300)]
            fgrid = np.array([model.density(th)[1] for th in sub])
            fmean = fgrid.mean(axis=0)
            modes_draws = np.array([harness.count_modes(model.s, f) for f in fgrid])
            p_mean = np.mean([model.density(th)[0] for th in sub], axis=0)
            mean_s = float(model.s @ p_mean)
            sd_s = float(np.sqrt(p_mean @ (model.s - mean_s) ** 2))
            skew = float((p_mean @ (model.s - mean_s) ** 3) / sd_s ** 3)
            out.update({
                tag + "_bracket_mean": br.mean(axis=0), tag + "_bracket_width90": np.diff(np.percentile(br, [5, 95], axis=0), axis=0)[0],
                tag + "_bracket_q": np.percentile(br, [5, 50, 95], axis=0),
                tag + "_meanF_mean": float(summ["mean_F"].mean()), tag + "_meanF_sd": float(summ["mean_F"].std()),
                tag + "_chi2_per_strike": float(summ["chi2"].mean() / len(K)), tag + "_max_abs_resid": float(np.abs(summ["resid"].mean(axis=0)).max()),
                tag + "_edge_mass": summ["edge_mass"].mean(axis=0), tag + "_tau_q": np.percentile(res["taus"], [5, 50, 95]),
                tag + "_rhat_max": res["rhat_max"], tag + "_ess_min": res["ess_min"], tag + "_divergences": res["divergences"],
                tag + "_bracket_rhat_max": float(act3.split_rhat(chains_br[:, :, keep]).max()) if keep.any() else 1.0,
                tag + "_bracket_ess_min": float(act3.ess(chains_br[:, :, keep]).min()) if keep.any() else float(br.shape[0]),
                tag + "_seconds": res["seconds"], tag + "_grid_s": model.s, tag + "_grid_f_mean": fmean,
                tag + "_grid_f_q": np.percentile(fgrid, [5, 95], axis=0),
                tag + "_n_modes": int(harness.count_modes(model.s, fmean)), tag + "_frac_draws_multimodal": float(np.mean(modes_draws >= 2)),
                tag + "_std_dollars": sd_s, tag + "_skew": skew, tag + "_mean_minus_F0_cents": 100.0 * (mean_s - F0),
            })
        # checks
        out["checks"] = {
            "act2_butterfly_free": bool(a2["svi"]["butterfly_free"]) if a2.get("ok") else None,
            "act2_density_nonneg": bool(a2["checks"]["density_nonneg"]) if a2.get("ok") else None,
            "act2_normalised": bool(a2["checks"]["normalised"]) if a2.get("ok") else None,
            "act2_mean_equals_forward": bool(a2["checks"]["mean_equals_forward"]) if a2.get("ok") else None,
            "act3_normalisation_edge_mass_ok": bool(out["act3_edge_mass"].max() < harness.EDGE_MASS_MAX),
            "act3_chi2_ok": bool(out["act3_chi2_per_strike"] < 2.0),
            "act3_max_resid_ok": bool(out["act3_max_abs_resid"] < 3.0),
            "mean_equals_forward_z": float((out["act3u_meanF_mean"] - F0) / max(out["act3u_meanF_sd"], 1e-9)),
            "mean_equals_forward_ok": bool(abs(out["act3u_meanF_mean"] - F0) < 3 * max(out["act3u_meanF_sd"], 1e-9)),
            "sampler_ok": bool(out["act3_rhat_max"] < 1.01 and out["act3_ess_min"] >= 400 and out["act3_divergences"] == 0),
            "sampler_bracket_ok": bool(out["act3_bracket_rhat_max"] < 1.05 and out["act3_bracket_ess_min"] >= 100),
        }
        out["detector"] = detector.gate(out.get("act2_bracket"), out["act3_bracket_mean"], int(len(K)))
    except Exception as exc:
        import traceback
        out["error"] = repr(exc)
        out["traceback"] = traceback.format_exc()
    out["seconds"] = time.time() - t0
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def run(only_dates: Optional[List[str]], snaps: List[str], workers: int) -> List[Dict[str, Any]]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_p = RESULTS / "runs.pkl"
    have: List[Dict[str, Any]] = pickle.load(open(out_p, "rb")) if out_p.exists() else []
    done = {(r["settle_date"], r["snap"], r.get("window_min", 60)) for r in have if r.get("error") is None}
    inp = load_inputs()
    jobs = [{"date": d, "snap": s, "window": w, "underlying": inp["underlying"], "settles": inp["settles"]}
            for d in inp["dates"] for s in snaps for w in WINDOWS
            if (only_dates is None or d["settle_date"] in only_dates) and (d["settle_date"], s, w) not in done]
    print("dates clearing Gate 0: %d; jobs to run: %d" % (len(inp["dates"]), len(jobs)), flush=True)
    if not jobs:
        return have
    ctx = mp.get_context("fork")
    t0 = time.time()
    results = [r for r in have if (r["settle_date"], r["snap"], r.get("window_min", 60)) in done]
    with ctx.Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(run_one, jobs), 1):
            results.append(r)
            print("  %3d/%d %s %s w%d %s %5.0fs %s" % (i, len(jobs), r["settle_date"], r["snap"], r["window_min"], "ERR" if r.get("error") else ("gate0=%s" % r.get("gate0")),
                                                   time.time() - t0, (r.get("detector") or {}).get("reason", "")[:60]), flush=True)
            with open(out_p, "wb") as fh:
                pickle.dump(results, fh)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma-separated settle dates")
    ap.add_argument("--snap", default=",".join(SNAPS))
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    if not a.report:
        run([x.strip() for x in a.only.split(",")] if a.only else None, [s.strip() for s in a.snap.split(",")], a.workers)
    from . import report_real
    rs = pickle.load(open(RESULTS / "runs.pkl", "rb"))
    summary = report_real.aggregate(rs)
    with open(RESULTS / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    report_real.plots(rs, PLOTS)
    text = report_real.render(summary, rs, PLOTS)
    (ROOT / "FINDINGS_REALCHAIN.md").write_text(text)
    print("wrote", ROOT / "FINDINGS_REALCHAIN.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
