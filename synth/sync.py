"""Quote synchronisation: move every quote in a snapshot window to one underlying level and
one time-to-expiry before anything is fitted.

Why. Gate 0 assembles a chain from the last quote per instrument inside a trailing window
(60 minutes). WTI moves $1+ in an hour in this regime, and at T = 1 day an ATM weekly
loses ~7c an hour to theta, so a "snapshot" is a set of quotes that describe different
underlying levels and different times. FINDINGS_REALCHAIN.md §1.2: the same dates at a
10-minute window fit 4x better (chi2/strike 8.1 -> 2.0) and lose their multimodality, but
the 10-minute window drops 70% of dates. This module recovers both.

What the data allows. There is no intraday futures price on disk: `futures_stats` carries
the 14:30 settlement and session high/low updates only (verified: one record between
13:30 and 14:35 ET on 2026-03-12 for CLJ6). So the underlying path inside the window is
estimated from the option trade stream itself - every TBBO record is a trade with the
option's own bid/ask at that instant, and an ATM quote with a 1c half-spread pins the
underlying to ~2c through its delta. The level of that path is then anchored to the NYMEX
settlement (the reference forward) when the snapshot is at 14:30, and to the chain's
parity forward otherwise; only the *shape* of the path comes from the options.

Method (sticky-strike, the default). For a quote at time t_i on strike K_i with mid m_i:
    sigma_i  = Black-76 implied vol of m_i at (F(t_i), K_i, T_i)      [the quote's own vol]
    m_i'     = Black-76 price at (F_ref, K_i, T_ref, sigma_i)
so the shift is exact under "this strike's implied vol did not change in the last
<window> minutes", which is the assumption a desk makes when it re-marks a sheet after
the underlying moves. It carries delta, gamma and theta together. Bid and ask move by the
same amount; the half-spread is untouched. Quotes at the tick floor (mid <= 1.5c) are not
moved (delta ~ 0); quotes below intrinsic are moved by the change in intrinsic value.

The sticky-moneyness alternative is also computed (`adjust(..., mode="moneyness")`): the
same shift but with the vol read off the window's fitted smile at the *new* moneyness. The
two differ at second order (smile slope x move); both are reported so the model dependence
of the adjustment is visible.

Path estimation. Three passes (the first with a flat smile at the ATM vol):
    1. implied vol of every two-sided event in the window at the current path
    2. weighted quadratic smile sigma^(k) in k = ln(K / F(t)) on OTM events (weights
       (vega/half-spread)^2, capped; one MAD-outlier pass)
    3. per event, the underlying level F_i that reprices its mid through sigma^(k)
       (bisection; weight (|delta| / half-spread)^2; |delta| < 0.05 events dropped)
    4. piecewise-linear path on 1-minute knots, weighted least squares with a random-walk
       prior whose step variance is the diffusion variance F^2 sigma_atm^2 dt - i.e. the
       path is shrunk toward "the underlying did not move" by exactly as much as a
       diffusion at the ATM vol says it should be
    5. level: F(t) = F_ref + (F^(t) - F^(t_anchor)); the options give the shape, the reference
       forward gives the level at the anchor instant. For the 14:30 snapshots the anchor is
       14:29, the middle of the two-minute settlement window the NYMEX settlement is the
       VWAP of, and the chain's forward is the path's value at 14:30 (the "anchor drift"
       F(t_ref) - F_settle is reported; it is the last minute's move). The offset
       F_ref - F^(t_anchor) is also reported: it is the options-implied level against the
       futures, a second measurement of the Stage 6 disagreement that uses every quote
       rather than only two-sided pairs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from . import black76

KNOT_MIN = 1.0          # path knots every minute: at 160% vol the underlying moves ~20c per minute, and 5-minute
                        # knots left chi2/strike at 3.7 where 1-minute knots reach 2.1 (probe on 2026-03-12 T-1d)
MIN_ABS_DELTA = 0.05    # events with less delta than this say nothing about the underlying
FLOOR_MID = 0.015       # 0.01/0.02 quotes: not moved
MIN_EVENTS = 5          # fewer informative events than this: path = flat at F_ref (theta-only)
YEAR_SEC = 365.0 * 86400.0


# --------------------------------------------------------------------------
# smile in log-moneyness: weighted quadratic with one outlier pass
# --------------------------------------------------------------------------

class Smile:
    def __init__(self, coef: np.ndarray, k_lo: float, k_hi: float, sigma_atm: float):
        self.coef = coef
        self.k_lo, self.k_hi = k_lo, k_hi
        self.sigma_atm = sigma_atm

    def __call__(self, k):
        kk = np.clip(np.asarray(k, float), self.k_lo, self.k_hi)  # constant beyond the fitted range
        return np.maximum(np.polyval(self.coef, kk), 0.02)


def fit_smile(k: np.ndarray, iv: np.ndarray, w: np.ndarray, sigma_default: float) -> Smile:
    k, iv, w = np.asarray(k, float), np.asarray(iv, float), np.asarray(w, float)
    good = np.isfinite(k) & np.isfinite(iv) & np.isfinite(w) & (w > 0) & (iv > 0.02) & (iv < 5.0)
    if good.sum() < 4:
        return Smile(np.array([sigma_default if good.sum() == 0 else float(np.median(iv[good]))]), -1.0, 1.0, sigma_default)
    k, iv, w = k[good], iv[good], w[good]
    w = np.minimum(w, np.percentile(w, 95))
    deg = 2 if k.size >= 6 and (k.max() - k.min()) > 0.02 else 1
    coef = np.polyfit(k, iv, deg, w=np.sqrt(w))
    resid = iv - np.polyval(coef, k)
    z = resid * np.sqrt(w)
    mad = 1.4826 * float(np.median(np.abs(z - np.median(z)))) + 1e-12
    keep = np.abs(z / mad) < 4.0
    if keep.sum() >= 4 and (~keep).any():
        coef = np.polyfit(k[keep], iv[keep], deg, w=np.sqrt(w[keep]))
    return Smile(coef, float(k.min()), float(k.max()), float(np.polyval(coef, 0.0)))


# --------------------------------------------------------------------------
# underlying level implied by one quote through the smile
# --------------------------------------------------------------------------

def implied_underlying(mid: np.ndarray, K: np.ndarray, T: np.ndarray, right: np.ndarray, D: float, smile: Smile,
                       F_lo: float, F_hi: float, n_iter: int = 50) -> np.ndarray:
    """Solve price(F, K, T, smile(ln K/F)) = mid for F by bisection, vectorised; NaN where the
    mid is not bracketed (below intrinsic anywhere in [F_lo, F_hi], or above the cap)."""
    mid, K, T = np.asarray(mid, float), np.asarray(K, float), np.asarray(T, float)
    right = np.asarray(right)

    def price_at(F):
        sig = smile(np.log(K / F))
        return black76.price(F, K, T, sig, D, right)
    lo = np.full(mid.shape, F_lo)
    hi = np.full(mid.shape, F_hi)
    is_call = right == "C"
    p_lo, p_hi = price_at(lo), price_at(hi)
    # calls increase in F, puts decrease: the bracket must straddle the mid
    ok = np.where(is_call, (p_lo <= mid) & (p_hi >= mid), (p_lo >= mid) & (p_hi <= mid))
    for _ in range(n_iter):
        m = 0.5 * (lo + hi)
        pm = price_at(m)
        go_up = np.where(is_call, pm < mid, pm > mid)
        lo = np.where(go_up, m, lo)
        hi = np.where(go_up, hi, m)
    F = 0.5 * (lo + hi)
    return np.where(ok, F, np.nan)


# --------------------------------------------------------------------------
# the path
# --------------------------------------------------------------------------

def _pl_basis(t: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Piecewise-linear interpolation matrix: rows sum to one."""
    A = np.zeros((t.size, knots.size))
    j = np.clip(np.searchsorted(knots, t, side="right") - 1, 0, knots.size - 2)
    frac = (t - knots[j]) / (knots[j + 1] - knots[j])
    frac = np.clip(frac, 0.0, 1.0)
    A[np.arange(t.size), j] = 1.0 - frac
    A[np.arange(t.size), j + 1] = frac
    return A


def fit_path(t_min: np.ndarray, F_obs: np.ndarray, w: np.ndarray, window_min: float, F_ref: float, sigma_atm: float,
             knot_min: float = KNOT_MIN) -> Dict[str, Any]:
    """t_min: minutes before the reference instant (>= 0). Returns knots (minutes before), values,
    and the fitted level at t = 0. Random-walk prior between knots with variance
    F_ref^2 sigma_atm^2 dt; two passes with a 4-MAD residual cut."""
    n_k = int(np.ceil(window_min / knot_min)) + 1
    knots = np.linspace(0.0, window_min, n_k)  # minutes before t_ref, ascending
    A = _pl_basis(np.asarray(t_min, float), knots)
    dt_years = (knot_min * 60.0) / YEAR_SEC
    step_var = (F_ref * max(sigma_atm, 0.05)) ** 2 * dt_years
    Dm = np.zeros((n_k - 1, n_k))
    for i in range(n_k - 1):
        Dm[i, i], Dm[i, i + 1] = -1.0, 1.0
    P = Dm.T @ Dm / step_var
    keep = np.isfinite(F_obs) & np.isfinite(w) & (w > 0)
    used = keep.copy()
    vals = np.full(n_k, F_ref)
    for _pass in range(2):
        if used.sum() == 0:
            break
        Ak, Fk, wk = A[used], F_obs[used], w[used]
        H = (Ak * wk[:, None]).T @ Ak + P + 1e-9 * np.eye(n_k)
        g = Ak.T @ (wk * Fk)
        vals = np.linalg.solve(H, g)
        resid = (F_obs - A @ vals)
        z = resid * np.sqrt(np.maximum(w, 0.0))
        zk = z[used]
        mad = 1.4826 * float(np.median(np.abs(zk - np.median(zk)))) + 1e-9
        new_used = keep & (np.abs(z / mad) < 4.0)
        if new_used.sum() >= max(3, int(0.5 * keep.sum())) and (new_used != used).any():
            used = new_used
            continue
        break
    level_at_ref = float(vals[0])
    resid = F_obs - A @ vals
    rms = float(np.sqrt(np.average(resid[used] ** 2, weights=w[used]))) if used.sum() else float("nan")
    return {"knots_min": knots, "values": vals, "level_at_ref": level_at_ref, "used": used, "resid": resid,
            "rms_resid_dollars": rms, "n_used": int(used.sum()), "range_dollars": float(vals.max() - vals.min())}


def estimate_path(events, t_ref, T_ref: float, F_ref: float, D: float, sigma_atm: float, window_min: float,
                  n_iter: int = 3, anchor_min: float = 0.0) -> Dict[str, Any]:
    """events: DataFrame with ts_event (UTC), strike, right, bid_px_00, ask_px_00 - every record in
    the window, not only the last per instrument. F_ref is the underlying level `anchor_min`
    minutes before t_ref. Returns the path (knots in minutes before t_ref), its value at t_ref
    (`F_at_ref`) and diagnostics."""
    import pandas as pd
    ev = events[(events["bid_px_00"] > 0) & (events["ask_px_00"] > events["bid_px_00"])].copy()
    out: Dict[str, Any] = {"n_events": int(len(ev)), "ok": False}
    if ev.empty:
        out["reason"] = "no two-sided events"
        return out
    t_min = ((pd.Timestamp(t_ref) - ev["ts_event"]).dt.total_seconds() / 60.0).values
    T_i = T_ref + t_min * 60.0 / YEAR_SEC
    K = ev["strike"].values.astype(float)
    R = ev["right"].values
    mid = 0.5 * (ev["bid_px_00"].values + ev["ask_px_00"].values)
    hs = 0.5 * (ev["ask_px_00"].values - ev["bid_px_00"].values)
    knots = np.linspace(0.0, window_min, int(np.ceil(window_min / KNOT_MIN)) + 1)
    path_vals = np.full(knots.size, F_ref)
    smile = Smile(np.array([sigma_atm]), -1.0, 1.0, sigma_atm)
    path = None
    for it in range(n_iter):
        F_t = np.interp(t_min, knots, path_vals)
        if it == 0:
            # first pass: a flat smile at the ATM vol. Fitting a smile before the path is known pools
            # vols computed at the wrong underlying level, and a $1 move is ~25 vol points ATM here.
            smile = Smile(np.array([sigma_atm]), -1.0, 1.0, sigma_atm)
        else:
            iv = black76.implied_vol(mid, F_t, K, T_i, D, R)
            otm = np.where(R == "C", K >= F_t, K < F_t)
            vega = black76.vega(F_t, K, T_i, np.where(np.isfinite(iv), iv, sigma_atm), D)
            w_iv = (vega / np.maximum(hs, 0.005)) ** 2
            sel = otm & np.isfinite(iv) & (mid > FLOOR_MID)
            smile = fit_smile(np.log(K[sel] / F_t[sel]), iv[sel], w_iv[sel], sigma_atm)
        # underlying implied by each event through the smile
        F_i = implied_underlying(mid, K, T_i, R, D, smile, F_ref - 8.0, F_ref + 8.0)
        sig_i = smile(np.log(K / np.where(np.isfinite(F_i), F_i, F_ref)))
        sT = sig_i * np.sqrt(np.maximum(T_i, 1e-9))
        d1 = (np.log(np.where(np.isfinite(F_i), F_i, F_ref) / K) + 0.5 * sT ** 2) / np.maximum(sT, 1e-9)
        from scipy.special import ndtr
        delta = np.where(R == "C", ndtr(d1), ndtr(d1) - 1.0) * D
        w_F = (np.abs(delta) / np.maximum(hs, 0.005)) ** 2
        inf = np.isfinite(F_i) & (np.abs(delta) >= MIN_ABS_DELTA) & (mid > FLOOR_MID)
        if inf.sum() < MIN_EVENTS:
            out.update({"reason": "%d informative events < %d" % (int(inf.sum()), MIN_EVENTS), "n_informative": int(inf.sum()),
                        "knots_min": knots, "values": path_vals, "level_offset_cents": None, "smile": smile,
                        "F_at_ref": float(path_vals[0]), "anchor_drift_cents": 100.0 * (float(path_vals[0]) - F_ref),
                        "range_dollars": float(path_vals.max() - path_vals.min()), "rms_resid_dollars": float("nan"), "n_used": 0})
            return out
        path = fit_path(t_min[inf], F_i[inf], w_F[inf], window_min, F_ref, smile.sigma_atm)
        # options give the shape, the reference forward gives the level at the anchor instant
        level_at_anchor = float(np.interp(anchor_min, knots, path["values"]))
        path_vals = F_ref + (path["values"] - level_at_anchor)
        out["level_offset_cents"] = 100.0 * (F_ref - level_at_anchor)
    out.update({"ok": True, "knots_min": knots, "values": path_vals, "smile": smile, "n_informative": int(inf.sum()),
                "F_at_ref": float(path_vals[0]), "anchor_drift_cents": 100.0 * (float(path_vals[0]) - F_ref),
                "n_used": path["n_used"], "rms_resid_dollars": path["rms_resid_dollars"], "range_dollars": path["range_dollars"],
                "event_t_min": t_min[inf], "event_F": F_i[inf], "event_w": w_F[inf], "event_used": path["used"]})
    return out


def path_at(path: Dict[str, Any], t_min) -> np.ndarray:
    return np.interp(np.asarray(t_min, float), path["knots_min"], path["values"])


# --------------------------------------------------------------------------
# the adjustment
# --------------------------------------------------------------------------

def adjust(K, right, bid, ask, t_min, path: Dict[str, Any], F_ref: float, T_ref: float, D: float,
           mode: str = "strike") -> Dict[str, Any]:
    """Shift each quote from (F(t_i), T_i) to (F_ref, T_ref). Returns new bid/ask/mid, the total
    shift and its theta-only component (dollars, per quote), and how each quote was handled."""
    K = np.asarray(K, float)
    right = np.asarray(right)
    bid, ask = np.asarray(bid, float), np.asarray(ask, float)
    t_min = np.asarray(t_min, float)
    mid = 0.5 * (bid + ask)
    T_i = T_ref + t_min * 60.0 / YEAR_SEC
    F_t = path_at(path, t_min)
    n = K.size
    adj = np.zeros(n)
    adj_theta = np.zeros(n)
    how = np.full(n, "vol", dtype=object)
    sign = np.where(right == "C", 1.0, -1.0)
    intr_t = D * np.maximum(sign * (F_t - K), 0.0)
    intr_ref = D * np.maximum(sign * (F_ref - K), 0.0)
    iv = black76.implied_vol(mid, F_t, K, T_i, D, right)
    if mode == "strike":
        sig_ref = iv
        sig_t = iv
    elif mode == "moneyness":
        smile = path["smile"]
        sig_t = smile(np.log(K / F_t))
        sig_ref = smile(np.log(K / F_ref))
    else:
        raise ValueError(mode)
    have = np.isfinite(iv) if mode == "strike" else np.ones(n, bool)
    p_ref = black76.price(F_ref, K, T_ref, np.where(have, sig_ref, 0.5), D, right)
    p_t = black76.price(F_t, K, T_i, np.where(have, sig_t, 0.5), D, right)
    p_theta = black76.price(F_t, K, T_ref, np.where(have, sig_t, 0.5), D, right)
    with np.errstate(invalid="ignore"):
        model_shift = p_ref - p_t
        theta_shift = p_theta - p_t
    floor = mid <= FLOOR_MID
    for i in range(n):
        if floor[i]:
            how[i] = "floor"
            continue
        if have[i] and np.isfinite(model_shift[i]):
            adj[i] = model_shift[i]
            adj_theta[i] = theta_shift[i]
        else:  # below intrinsic or above the cap: move with intrinsic value only
            adj[i] = intr_ref[i] - intr_t[i]
            how[i] = "intrinsic"
    new_bid = np.maximum(bid + adj, 0.005)
    new_ask = np.maximum(ask + adj, new_bid + 0.005)
    return {"bid": new_bid, "ask": new_ask, "mid": 0.5 * (new_bid + new_ask), "hs": 0.5 * (new_ask - new_bid),
            "adj": adj, "adj_theta": adj_theta, "adj_delta": adj - adj_theta, "how": how, "F_t": F_t, "T_i": T_i, "iv": iv}
