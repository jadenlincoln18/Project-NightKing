"""Real strike geometry and real half-spreads from the stored CME TBBO.

For every (root, expiry) in data_cme/parquet/chain_density and each lookback
(1 and 2 business days before settlement, at 14:30 ET), take the last quote per
instrument in the trailing 60 minutes, derive the forward from put-call parity on
strikes quoting both sides, keep the OTM side per strike, and record
(strike, right, mid, half-spread). The result is written to synth/geometry.json
so the harness and CI can run without data_cme/ present.

The half-spread model is a power law in the quote's mid with lognormal scatter,
floored at the half-tick; it is fitted on every OTM quote in the snapshots and
its parameters are stored alongside the snapshots. Both the per-strike observed
half-spreads and the fitted model are available to the noise generator.

    python3 -m synth.geometry            # rebuild synth/geometry.json from data_cme/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEOMETRY_PATH = HERE / "geometry.json"
DATA_CME = ROOT / "data_cme" / "parquet"
FRESH_MIN = 60
LOOKBACK_DAYS = (1, 2)
TICK = 0.01
ET = "America/New_York"


def load(path: Path = GEOMETRY_PATH) -> Dict[str, Any]:
    with open(path) as fh:
        return json.load(fh)


def snapshots(geo: Optional[Dict[str, Any]] = None, min_strikes: int = 8, min_wing: int = 3,
              lookback: Optional[int] = None) -> List[Dict[str, Any]]:
    geo = geo or load()
    out = []
    for s in geo["snapshots"]:
        if lookback is not None and s["lookback_days"] != lookback:
            continue
        if s["n_strikes"] < min_strikes or s["n_below"] < min_wing or s["n_above"] < min_wing:
            continue
        out.append(s)
    return out


# --------------------------------------------------------------------------
# extraction from data_cme
# --------------------------------------------------------------------------

def _parity_forward(last, D: float = 1.0) -> Optional[float]:
    """Median of K + (C - P)/D over strikes quoting both a call and a put, weighted
    toward the tightest pairs."""
    piv = last.pivot_table(index="strike", columns="right", values=["mid", "hs"])
    if ("mid", "C") not in piv.columns or ("mid", "P") not in piv.columns:
        return None
    both = piv.dropna(subset=[("mid", "C"), ("mid", "P")])
    if len(both) < 2:
        return None
    f = both.index.values + (both[("mid", "C")].values - both[("mid", "P")].values) / D
    w = 1.0 / (both[("hs", "C")].values + both[("hs", "P")].values + 0.005)
    order = np.argsort(f)
    cw = np.cumsum(w[order]) / w.sum()
    return float(f[order][np.searchsorted(cw, 0.5)])


def _snapshot(tb, settle_ts, snap_ts, T_years: float) -> Optional[Dict[str, Any]]:
    import pandas as pd
    w = tb[(tb["ts_event"] <= snap_ts) & (tb["ts_event"] > snap_ts - pd.Timedelta(minutes=FRESH_MIN))]
    if w.empty:
        return None
    last = w.sort_values("ts_event").groupby("instrument_id").tail(1).copy()
    last = last[last["bid_px_00"].notna() & last["ask_px_00"].notna() & (last["bid_px_00"] > 0)
                & (last["ask_px_00"] > last["bid_px_00"])]
    if last.empty:
        return None
    last["hs"] = (last["ask_px_00"] - last["bid_px_00"]) / 2.0
    last["mid"] = (last["ask_px_00"] + last["bid_px_00"]) / 2.0
    F = _parity_forward(last)
    if F is None:
        return None
    otm = np.where(last["right"] == "C", last["strike"] >= F, last["strike"] < F)
    o = last[otm].sort_values("strike")
    # one quote per strike (if both sides survive at the ATM strike keep the tighter)
    o = o.sort_values(["strike", "hs"]).drop_duplicates("strike", keep="first")
    # ATM vol from the nearest strikes on each side (for planting realistic vols)
    from . import black76
    near = o.iloc[(o["strike"] - F).abs().argsort()[:4]]
    iv = black76.implied_vol(near["mid"].values, F, near["strike"].values, T_years, 1.0, near["right"].values)
    iv = iv[np.isfinite(iv)]
    return {
        "forward": F,
        "T_years": T_years,
        "atm_iv": float(np.median(iv)) if iv.size else None,
        "strikes": [float(x) for x in o["strike"]],
        "rights": list(o["right"]),
        "mids": [float(x) for x in o["mid"]],
        "half_spreads": [float(x) for x in o["hs"]],
        "n_strikes": int(len(o)),
        "n_below": int((o["strike"] < F).sum()),
        "n_above": int((o["strike"] > F).sum()),
    }


def fit_half_spread_model(mids: np.ndarray, hs: np.ndarray) -> Dict[str, float]:
    """log(hs) = alpha + beta*log(mid) + eps, eps ~ N(0, tau^2); fitted on quotes above
    the half-tick floor so the floor does not drag the slope."""
    m = np.asarray(mids, float)
    h = np.asarray(hs, float)
    ok = (h > TICK / 2 + 1e-9) & (m > 0)
    x = np.log(m[ok])
    y = np.log(h[ok])
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    return {"alpha": float(coef[0]), "beta": float(coef[1]), "tau": float(resid.std(ddof=2)),
            "floor": TICK / 2, "n_fit": int(ok.sum()), "n_at_floor": int((~ok).sum()),
            "frac_at_floor": float((~ok).mean())}


def build(out_path: Path = GEOMETRY_PATH) -> Dict[str, Any]:
    import pandas as pd
    cd = pd.read_parquet(DATA_CME / "chain_density" / "part.parquet")
    cd = cd[cd["root"] != "MCO"]
    snaps: List[Dict[str, Any]] = []
    all_mid: List[float] = []
    all_hs: List[float] = []
    for r in cd.itertuples():
        p = DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % r.root) / ("expiry=%s" % r.settle_date) / "part.parquet"
        if not p.exists():
            continue
        tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
        settle = pd.Timestamp("%s 14:30" % r.settle_date, tz=ET)
        for lb in LOOKBACK_DAYS:
            snap = settle - pd.tseries.offsets.BDay(lb)
            T = (settle - snap).total_seconds() / (365.0 * 86400.0)
            s = _snapshot(tb, settle.tz_convert("UTC"), snap.tz_convert("UTC"), T)
            if s is None:
                continue
            s.update({"root": r.root, "settle_date": str(r.settle_date), "snap_time_et": snap.strftime("%Y-%m-%d %H:%M"),
                      "lookback_days": lb})
            snaps.append(s)
            all_mid.extend(s["mids"])
            all_hs.extend(s["half_spreads"])
    model = fit_half_spread_model(np.array(all_mid), np.array(all_hs))
    counts = np.array([s["n_strikes"] for s in snaps])
    geo = {
        "source": "data_cme/parquet/options_tbbo_by_expiry, last quote per instrument in the trailing %d min" % FRESH_MIN,
        "lookback_days": list(LOOKBACK_DAYS),
        "half_spread_model": model,
        "n_snapshots": len(snaps),
        "strike_count_quantiles": {str(q): float(np.percentile(counts, q)) for q in (0, 10, 25, 50, 75, 90, 100)} if counts.size else {},
        "snapshots": snaps,
    }
    tmp = out_path.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump(geo, fh, indent=1)
    tmp.replace(out_path)
    return geo


def main(argv=None) -> int:
    geo = build()
    m = geo["half_spread_model"]
    print("snapshots: %d   strike-count quantiles: %s" % (geo["n_snapshots"], geo["strike_count_quantiles"]))
    print("half-spread model: log hs = %.3f + %.3f log mid, tau=%.3f  (%.0f%% of quotes at the half-tick floor)"
          % (m["alpha"], m["beta"], m["tau"], 100 * m["frac_at_floor"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
