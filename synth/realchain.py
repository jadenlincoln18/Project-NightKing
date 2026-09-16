"""Step 2 (V2): the extractor on real KXWTIW chains, descriptively only, with the three
changes of NightKing/HANDOFF_forward_and_sync_fix.md run as separate arms so that each
change's effect is attributable:

    base   V1 exactly: parity forward from the raw window, no synchronisation
    fwd    forward from the NYMEX settlement of the option's own underlying (T-2d, T-1d,
           T-0 at 14:30 ET); parity demoted to a check. T-4h has no futures print at
           10:30 ET, so it keeps the parity forward there.
    sync   fwd + every quote in the window moved to the snapshot instant and to one
           underlying level before fitting (synth/sync.py, sticky-strike)
    sync_m the same with the sticky-moneyness shift; T-1d / 60 min only (sensitivity)

All arms carry the new Gate 4 (synth/detector.py: split-half Act III consistency, Laplace
leave-one-out residuals, Act II reported), so the detector change is also before/after.

No Kalshi prices are read, no gap is computed, nothing is evaluated as a trade. Dates,
snapshots, windows and sampler settings are those of FINDINGS_REALCHAIN.md:

    T-2d   14:30 ET two business days before settlement
    T-1d   14:30 ET one business day before
    T-4h   10:30 ET on settlement day
    T-0    14:30 ET on settlement day: parity forward only (the chain is at intrinsic)

    python3 -m synth.realchain                        # run every arm (resumable), then report
    python3 -m synth.realchain --arms sync            # one arm
    python3 -m synth.realchain --report               # re-render from what is on disk
    python3 -m synth.realchain --only 2026-03-13 --snap T-1d --arms sync
    python3 -m synth.realchain --calibrate            # split-half null on synthetic chains
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
PLOTS = HERE / "plots_real_v2"
RUNS_V1 = RESULTS / "runs.pkl"
RUNS_V2 = RESULTS / "runs_v2.pkl"
ET = "America/New_York"
FRESH_MIN = 60
SNAPS = ("T-2d", "T-1d", "T-4h", "T-0")
SETTLE_SNAPS = ("T-2d", "T-1d", "T-0")   # 14:30 ET: a NYMEX settlement exists for the snapshot instant
NUTS = {"n_chains": 4, "n_warmup": 400, "n_samples": 400}
SERIES = "KXWTIW"
WINDOWS = (60, 10)   # minutes: Gate 0's own window, and a near-synchronous one (the underlying moves)
RATE = 0.04          # D = exp(-r T): fixed analytically. At T <= 2 days D is within 2e-4 of 1, i.e. < 0.02c on any
                     # price here; the chain cannot identify it (V1: 0.947 at expiry) and the forward no longer
                     # depends on the regression slope, so there is nothing left for the slope to do.
ARMS = ("base", "fwd", "sync", "sync_m", "real")
ARM_SNAPS = {"sync_m": {("T-1d", 60)}}   # sensitivity arm: T-1d / 60 min only
INTRADAY = DATA_CME / "futures_intraday" / "schema=ohlcv-1m"   # Task 2 pull (db_pull_futures.py); the `real` arm needs it
SE_FLOOR_FUTURES = 0.02   # 2c floor on the Stage 14 tolerance when the forward comes from the futures
ANCHOR_MIN = 1.0          # the NYMEX settlement is the VWAP of 14:28-14:30; anchor the path at 14:29
PARITY_Z = 3.0            # parity check: flag |parity - futures| > PARITY_Z se and > PARITY_ABS_CENTS
PARITY_ABS_CENTS = 10.0


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
    intraday = {p.parent.name.split("=", 1)[1]: str(p) for p in INTRADAY.glob("symbol=*/part.parquet")} if INTRADAY.exists() else {}
    return {"dates": dates, "underlying": under, "settles": settles, "intraday": intraday}


def load_bars(path: str, t_lo, t_hi):
    """ohlcv-1m bars of one contract between two UTC timestamps (bar open time)."""
    import pandas as pd
    b = pd.read_parquet(path, columns=["ts_event", "open", "high", "low", "close", "volume"])
    b["ts_event"] = pd.to_datetime(b["ts_event"], utc=True)
    return b[(b["ts_event"] >= t_lo) & (b["ts_event"] < t_hi)].sort_values("ts_event")


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


def window_events(tb, snap_ts, window_min: int = FRESH_MIN):
    """Every TBBO record in the trailing window (the path estimator uses all of them)."""
    import pandas as pd
    return tb[(tb["ts_event"] <= snap_ts) & (tb["ts_event"] > snap_ts - pd.Timedelta(minutes=window_min))]


def snapshot(tb, snap_ts, window_min: int = FRESH_MIN):
    """Last quote per instrument in the trailing window with a real two-sided market."""
    w = window_events(tb, snap_ts, window_min)
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


def parity_on(q, D_fixed: float):
    """Stage 6 on the strikes quoting both sides. Returns (result dict or None, free-D result or None, n_both)."""
    from . import stage6
    piv = q.pivot_table(index="strike", columns="right", values=["mid", "hs", "age_min"])
    if ("mid", "C") not in piv.columns or ("mid", "P") not in piv.columns:
        return None, None, 0
    both = piv.dropna(subset=[("mid", "C"), ("mid", "P")])
    if len(both) < 2:
        return None, None, int(len(both))
    wts = 1.0 / (both[("hs", "C")].values ** 2 + both[("hs", "P")].values ** 2)
    st6 = stage6.parity_forward(both.index.values, both[("mid", "C")].values, both[("mid", "P")].values, weights=wts, fixed_D=D_fixed)
    st6_free = (stage6.parity_forward(both.index.values, both[("mid", "C")].values, both[("mid", "P")].values, weights=wts)
                if len(both) >= 3 else None)
    return st6, st6_free, int(len(both))


# --------------------------------------------------------------------------
# one (date, snapshot, window, arm)
# --------------------------------------------------------------------------

def run_one(job: Dict[str, Any]) -> Dict[str, Any]:
    import pandas as pd
    from . import act2, act3, densities, detector, geometry, harness, sync
    d, label, window, arm = job["date"], job["snap"], int(job.get("window", 60)), job.get("arm", "base")
    out: Dict[str, Any] = {"settle_date": d["settle_date"], "root": d["root"], "snap": label, "window_min": window, "arm": arm,
                           "event_ticker": d["event_ticker"], "cl_contract_kalshi": d["cl_contract"], "ice_settle": d["ice_settle"],
                           "error": None}
    t0 = time.time()
    try:
        p = DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % d["root"]) / ("expiry=%s" % d["settle_date"]) / "part.parquet"
        tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
        times = snapshot_times(d["settle_ts"])
        snap_ts = times[label]
        snap_utc = snap_ts.tz_convert("UTC")
        out["snap_time_et"] = snap_ts.strftime("%Y-%m-%d %H:%M")
        T = max((pd.Timestamp(d["settle_ts"]) - snap_utc).total_seconds() / (365.0 * 86400.0), 0.0)
        out["T_years"] = T
        D = float(np.exp(-RATE * T))
        out["D_used"] = D
        q = snapshot(tb, snap_utc, window)
        if q is None:
            out["gate0"] = False
            out["gate0_reason"] = "no two-sided quotes in the window"
            return out
        out["n_quoted_strikes"] = int(q["strike"].nunique())  # Gate 0's own count: any side, any strike
        out["gate0_pooled"] = bool(out["n_quoted_strikes"] >= 8)
        # the independent forward: NYMEX settlement of the option's own underlying, same instant
        under = job["underlying"].get((d["root"], d["settle_date"]))
        out["underlying"] = under
        out["contract_month_match"] = (under == d["cl_contract"]) if under else None
        snap_date = snap_ts.strftime("%Y-%m-%d")
        F_settle = job["settles"].get((snap_date, under)) if (under and label in SETTLE_SNAPS) else None
        out["nymex_settle_same_day"] = F_settle
        # Stage 6 on the raw window (every arm reports it)
        st6, st6_free, n_both = parity_on(q, D)
        out["two_sided_strikes"] = n_both
        out["D_chain"] = float(st6_free["D"]) if st6_free and st6_free["ok"] else None
        out["F0_parity_freeD"] = float(st6_free["F0"]) if st6_free and st6_free["ok"] else None
        have_parity = bool(st6 is not None and st6["ok"] and np.isfinite(st6["F0"]))
        if have_parity:
            se_raw = float(st6["se_F0"])
            if n_both < 3:
                se_raw = max(se_raw, 0.10)  # two pairs: no residual degrees of freedom; a nominal 10c
            out.update({"F0_parity": float(st6["F0"]), "se_F0_parity": se_raw, "parity_pairs": int(st6["n_pairs"]),
                        "parity_flagged": int(st6["flagged"].sum()), "parity_resid_sd": float(st6["resid_sd"])})
            if F_settle is not None:
                out["parity_minus_nymex_cents"] = 100.0 * (out["F0_parity"] - F_settle)
            if label == "T-0" and d["ice_settle"] is not None:
                out["parity_minus_ice_cents"] = 100.0 * (out["F0_parity"] - d["ice_settle"])
        # --- the forward, by arm ---------------------------------------------------
        sync_mode = {"sync": "strike", "sync_m": "moneyness", "real": "strike"}.get(arm)
        if arm == "base" or (arm == "fwd" and F_settle is None):
            if not have_parity:
                out["gate0"] = False
                out["gate0_reason"] = "fewer than 2 two-sided strikes for parity"
                return out
            F0, se = out["F0_parity"], out["se_F0_parity"]
            out["forward_source"] = "parity"
        elif arm == "fwd":
            F0 = float(F_settle)
            se = max(out.get("se_F0_parity", SE_FLOOR_FUTURES), SE_FLOOR_FUTURES) if have_parity else 0.10
            out["forward_source"] = "futures"
        else:  # sync arms
            if F_settle is not None:
                anchor, anchor_min = float(F_settle), ANCHOR_MIN
            elif have_parity:
                anchor, anchor_min = out["F0_parity"], 0.0
            else:
                out["gate0"] = False
                out["gate0_reason"] = "no futures print and fewer than 2 two-sided strikes for parity"
                return out
            asig0 = act3.atm_sigma(q["strike"].values, q["right"].values, q["mid"].values, anchor, D, T)
            events = window_events(tb, snap_utc, window)
            recon = sync.estimate_path(events, snap_utc, T, anchor, D, asig0, window, anchor_min=anchor_min)
            path = recon
            if arm == "real":
                bars_path = job.get("intraday", {}).get(under) if under else None
                if bars_path is None:
                    out["gate0"] = False
                    out["gate0_reason"] = "no intraday bars for %s" % under
                    return out
                bars = load_bars(bars_path, snap_utc - pd.Timedelta(minutes=window + 3), snap_utc + pd.Timedelta(minutes=1))
                path = sync.real_path_from_bars(bars, snap_utc, window, fallback=recon)
                cmp = sync.compare_paths(path, recon, anchor_min)
                out["real_path"] = {"n_bars": path["n_bars"], "coverage": path["coverage"], "source": path["source"], "n_from_fallback": path.get("n_from_fallback", 0),
                                    "n_interpolated": path.get("n_interpolated", 0), "leading_hole_min": path.get("leading_hole_min"),
                                    "level_at_ref": path["F_at_ref"], "recon_level_at_ref": recon["F_at_ref"],
                                    "real_minus_recon_at_ref_cents": 100.0 * (path["F_at_ref"] - recon["F_at_ref"]),
                                    "real_at_anchor_minus_anchor_cents": 100.0 * (float(np.interp(anchor_min, path["knots_min"], path["values"])) - anchor),
                                    "diff_dollars": cmp["diff_dollars"], "diff_shape_dollars": cmp["diff_shape_dollars"], "dist_from_anchor_min": cmp["dist_from_anchor_min"],
                                    "level_diff_at_anchor_dollars": cmp["level_diff_at_anchor_dollars"],
                                    "shape_rmse_cents": 100.0 * float(np.sqrt(np.mean(cmp["diff_shape_dollars"] ** 2))),
                                    "shape_max_abs_cents": 100.0 * float(np.abs(cmp["diff_shape_dollars"]).max()),
                                    "recon_ok": bool(recon.get("ok"))}
            adj = sync.adjust(q["strike"].values, q["right"].values, q["bid_px_00"].values, q["ask_px_00"].values,
                              q["age_min"].values, path, path["F_at_ref"], T, D, mode=sync_mode)
            q = q.copy()
            q["bid_px_00"], q["ask_px_00"], q["mid"], q["hs"] = adj["bid"], adj["ask"], adj["mid"], adj["hs"]
            out["sync"] = {"ok": bool(recon["ok"]), "reason": recon.get("reason"), "n_events": recon["n_events"],
                           "n_informative": recon.get("n_informative"), "n_used": recon.get("n_used"),
                           "path_range_dollars": path.get("range_dollars"), "path_rms_resid_dollars": recon.get("rms_resid_dollars"),
                           "level_offset_cents": recon.get("level_offset_cents"),
                           "anchor_drift_cents": 100.0 * (path["F_at_ref"] - anchor) if arm == "real" else recon.get("anchor_drift_cents"),
                           "path_source": path.get("source", "reconstruction"),
                           "anchor": anchor, "anchor_min": anchor_min, "mode": sync_mode,
                           "adj_rms_cents": float(100.0 * np.sqrt(np.mean(adj["adj"] ** 2))),
                           "adj_max_abs_cents": float(100.0 * np.abs(adj["adj"]).max()),
                           "adj_theta_rms_cents": float(100.0 * np.sqrt(np.mean(adj["adj_theta"] ** 2))),
                           "adj_delta_rms_cents": float(100.0 * np.sqrt(np.mean(adj["adj_delta"] ** 2))),
                           "how": {k: int(v) for k, v in zip(*np.unique(adj["how"].astype(str), return_counts=True))},
                           "path_knots_min": path["knots_min"], "path_values": path["values"]}
            st6a, _, n_both_a = parity_on(q, D)
            have_adj = bool(st6a is not None and st6a["ok"] and np.isfinite(st6a["F0"]))
            if have_adj:
                se_adj = float(st6a["se_F0"])
                if n_both_a < 3:
                    se_adj = max(se_adj, 0.10)
                out.update({"F0_parity_sync": float(st6a["F0"]), "se_F0_parity_sync": se_adj, "parity_pairs_sync": int(st6a["n_pairs"]),
                            "parity_flagged_sync": int(st6a["flagged"].sum())})
                if F_settle is not None:
                    out["parity_sync_minus_nymex_cents"] = 100.0 * (out["F0_parity_sync"] - F_settle)
                    out["parity_sync_minus_F0_cents"] = 100.0 * (out["F0_parity_sync"] - path["F_at_ref"])
                if label == "T-0" and d["ice_settle"] is not None:
                    out["parity_sync_minus_ice_cents"] = 100.0 * (out["F0_parity_sync"] - d["ice_settle"])
            if arm == "real" and path.get("source") == "real":
                F0 = float(path["F_at_ref"])
                se = max(se_adj, SE_FLOOR_FUTURES) if have_adj else 0.10
                out["forward_source"] = "futures (intraday)"
            elif F_settle is not None:
                F0 = float(path["F_at_ref"])
                se = max(se_adj, SE_FLOOR_FUTURES) if have_adj else 0.10
                out["forward_source"] = "futures+path"
            else:
                if not have_adj:
                    out["gate0"] = False
                    out["gate0_reason"] = "fewer than 2 two-sided strikes for parity (synchronised)"
                    return out
                F0, se = out["F0_parity_sync"], se_adj
                out["forward_source"] = "parity (synchronised)"
        out.update({"F0": float(F0), "se_F0": float(se)})
        # the parity check (every arm): raw parity vs the futures, and the arm's own chain vs its forward
        if have_parity and F_settle is not None:
            diff = out["parity_minus_nymex_cents"]
            z = diff / (100.0 * out["se_F0_parity"])
            out["parity_check"] = {"diff_cents": diff, "z": z, "flagged": bool(abs(z) > PARITY_Z and abs(diff) > PARITY_ABS_CENTS)}
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
        psi_map = None
        for mart, tag in ((True, "act3"), (False, "act3u")):
            model = act3.Model(K, R, mid, hs, F0, D, T, asig, se_F0=se, martingale=mart)
            rng = np.random.default_rng(1 if mart else 2)
            res = act3.sample(model, rng, sampler="nuts", **NUTS)
            if mart:
                psi_map = res["psi_map"]
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
                tag + "_bracket_q": np.percentile(br, [5, 50, 95], axis=0), tag + "_bracket_var": br.var(axis=0, ddof=1),
                tag + "_meanF_mean": float(summ["mean_F"].mean()), tag + "_meanF_sd": float(summ["mean_F"].std()),
                tag + "_chi2_per_strike": float(summ["chi2"].mean() / len(K)), tag + "_max_abs_resid": float(np.abs(summ["resid"].mean(axis=0)).max()),
                tag + "_resid_mean": summ["resid"].mean(axis=0),
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
        # Gate 4 (new): split-half consistency + LOO; Act II reported
        t1 = time.time()
        split = detector.split_half(K, R, mid, hs, F0, D, T, asig, se, edges, NUTS, seed=3)
        out["split_half"] = split
        out["split_half_seconds"] = time.time() - t1
        t1 = time.time()
        lo = detector.loo(K, R, mid, hs, F0, D, T, asig, se, psi_warm=psi_map)
        out["loo"] = lo
        out["loo_seconds"] = time.time() - t1
        out["act2_signal"] = detector.act2_signal(out.get("act2_bracket"), out["act3_bracket_mean"], int(len(K)))
        out["detector"] = detector.gate(split, lo, out["act2_signal"])
        out["detector_v1"] = out["act2_signal"]  # the V1 gate, for the before/after table
    except Exception as exc:
        import traceback
        out["error"] = repr(exc)
        out["traceback"] = traceback.format_exc()
    out["seconds"] = time.time() - t0
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def _key(r: Dict[str, Any]) -> Tuple[str, str, int, str]:
    return (r["settle_date"], r["snap"], int(r.get("window_min", 60)), r.get("arm", "base"))


def run(only_dates: Optional[List[str]], snaps: List[str], arms: List[str], workers: int, windows=WINDOWS) -> List[Dict[str, Any]]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    have: List[Dict[str, Any]] = pickle.load(open(RUNS_V2, "rb")) if RUNS_V2.exists() else []
    done = {_key(r) for r in have if r.get("error") is None}
    inp = load_inputs()
    jobs = [{"date": d, "snap": s, "window": w, "arm": a, "underlying": inp["underlying"], "settles": inp["settles"], "intraday": inp["intraday"]}
            for a in arms for d in inp["dates"] for s in snaps for w in windows
            if (only_dates is None or d["settle_date"] in only_dates) and (d["settle_date"], s, w, a) not in done
            and (a not in ARM_SNAPS or (s, w) in ARM_SNAPS[a])]
    print("dates clearing Gate 0: %d; jobs to run: %d (arms %s)" % (len(inp["dates"]), len(jobs), ",".join(arms)), flush=True)
    if not jobs:
        return have
    ctx = mp.get_context("fork")
    t0 = time.time()
    results = [r for r in have if _key(r) in done]
    with ctx.Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(run_one, jobs), 1):
            results.append(r)
            print("  %3d/%d %s %s w%d %-6s %s %5.0fs %s" % (i, len(jobs), r["settle_date"], r["snap"], r["window_min"], r["arm"],
                                                        "ERR" if r.get("error") else ("gate0=%s" % r.get("gate0")),
                                                        time.time() - t0, (r.get("detector") or {}).get("reason", "")[:70]), flush=True)
            if r.get("error"):
                print("      " + r["error"][:200], flush=True)
            tmp = RUNS_V2.with_name(RUNS_V2.name + ".tmp")
            with open(tmp, "wb") as fh:
                pickle.dump(results, fh)
            os.replace(tmp, RUNS_V2)   # atomic: a kill mid-dump leaves the previous checkpoint intact
    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma-separated settle dates")
    ap.add_argument("--snap", default=",".join(SNAPS))
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--windows", default=",".join(str(w) for w in WINDOWS))
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--calibrate", action="store_true", help="split-half null distribution on synthetic chains")
    a = ap.parse_args(argv)
    if a.calibrate:
        from . import calibrate_detector
        calibrate_detector.main(["--workers", str(a.workers)])
        return 0
    if not a.report:
        run([x.strip() for x in a.only.split(",")] if a.only else None, [s.strip() for s in a.snap.split(",")],
            [x.strip() for x in a.arms.split(",")], a.workers, tuple(int(w) for w in a.windows.split(",")))
    from . import report_real
    rs = pickle.load(open(RUNS_V2, "rb"))
    v1 = pickle.load(open(RUNS_V1, "rb")) if RUNS_V1.exists() else []
    summary = report_real.aggregate_v2(rs, v1)
    with open(RESULTS / "summary_v2.json", "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    report_real.plots_v2(rs, PLOTS)
    text = report_real.render_v2(summary, rs, PLOTS)
    target = ROOT / ("FINDINGS_REALCHAIN_V3.md" if "real" in summary["arms"] else "FINDINGS_REALCHAIN_V2.md")
    target.write_text(text)
    print("wrote", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
