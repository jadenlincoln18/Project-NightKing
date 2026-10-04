"""The backtest: extracted densities against Kalshi bracket prices, under BACKTEST_PROTOCOL.md.

The extractor is frozen (synth.realchain arm `real_m48_f1`: 48 knots, Gaussian prior, real intraday path, 1c tick
floor). This module adds Act IV: Stage 16 (every posterior draw integrated over Kalshi's exact bracket edges),
Stage 17 (the gap on the executable side), Stage 18 (per-draw logit decomposition), Stage 19 (the filter at the
thresholds of the protocol), hold-to-settlement P&L with the four-leg outer condor, and the denominator log.

    python3 -m synth.backtest                       # KXWTIW, T-1d and T-4h, resumable; then the report
    python3 -m synth.backtest --series KXWTI        # the secondary arm
    python3 -m synth.backtest --report              # re-render FINDINGS_BACKTEST.md from what is on disk
    python3 -m synth.backtest --only 2026-03-13 --snap T-1d

Results: synth/results_backtest/runs_<series>.pkl (one checkpoint per completed job, atomic), denominator_<series>.csv,
brackets_<series>.csv, backtest.log (timestamped; the first Kalshi price read is logged there).
"""

from __future__ import annotations

import argparse
import csv
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
KALSHI = ROOT / "data" / "parquet"
RESULTS = HERE / "results_backtest"
LOG = RESULTS / "backtest.log"

# --- the protocol's parameters (BACKTEST_PROTOCOL.md §3-§5); changing one here is a protocol change -------------
ARM = "real_m48_f1"
SNAPS = ("T-1d", "T-4h")
LEAD_SNAP = "T-1d"
WINDOW_MIN = 60
KALSHI_STALE_MAX_MIN = 10.0     # the snapshot bar, else the latest bar ending within this many minutes
PRICE_MIN, PRICE_MAX = 0.02, 0.98
BAND_MAX = 0.20
TROUGH_DIP = 0.02               # an interior local minimum must sit >= 2% below the lower neighbouring peak
TROUGH_FLOOR = 0.02             # ... and both peaks must be >= 2% of the density maximum
LOO_NEAR_EDGE = 1.00            # dollars
KALSHI_FEE_COEF = 0.07
CME_FEE_PER_LEG = 2.37          # $ per contract per side: 1.50 exchange+clearing, 0.02 NFA, 0.85 commission (assumption)
CME_EXIT_FRACTION = 0.5
SPREAD_WIDTH = 0.50             # $/bbl, the outer condor's spread width
BBL = {"CL": 1000, "MCO": 100}
SIZE_APPLICABLE = 500           # Kalshi contracts per standard-CL structure on a weekly date
SIZE_DEPTH_CLEARED = 50         # the size the depth scan cleared (Micro) - not available on weekly dates
LEG_SHIFT_MAX = 2               # at most two 0.25 steps outward when a replicating strike is unquoted
LEG_MAX_AGE_MIN = 5.0           # a TBBO leg quote older than this at the snapshot is not an executable price (amendment 5)
CONTRACT_TOL = 0.011            # Kalshi settlement vs NYMEX settlement of the matched contract: equal to the cent, else check the other months
SAMPLER_RHAT, SAMPLER_ESS = 1.05, 100
LOGIT_CLIP = 1e-3
STAGE18_MID_MIN, STAGE18_MID_MAX = 0.01, 0.99


def log(msg: str) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a") as fh:
        fh.write(line + "\n")


# --------------------------------------------------------------------------
# Kalshi side: edges, markets, candles
# --------------------------------------------------------------------------

def market_edges(strike_type: Any, floor: Any, cap: Any) -> Tuple[float, float]:
    """Kalshi quotes brackets in cents of the underlying: '$84.00 to $84.99' pays for 84.00 <= S <= 84.99, so in
    continuous price space the bracket is [83.995, 84.995); 'Above $95.99' is S >= 96.00, i.e. (95.995, inf)."""
    st = (strike_type or "").lower()
    f = float(floor) if floor is not None and floor == floor else None
    c = float(cap) if cap is not None and cap == cap else None
    if st == "between" and f is not None and c is not None:
        return round(f - 0.005, 3), round(c + 0.005, 3)
    if st in ("greater", "greater_or_equal") and f is not None:
        return round(f + 0.005 if st == "greater" else f - 0.005, 3), np.inf
    if st in ("less", "less_or_equal") and c is not None:
        return -np.inf, round(c - 0.005 if st == "less" else c + 0.005, 3)
    raise ValueError("unrecognised bracket: %r %r %r" % (strike_type, floor, cap))


def edges_from_subtitle(sub: str) -> Optional[Tuple[float, float]]:
    """Independent read of the sub-title, to verify market_edges against the text."""
    import re
    s = sub.replace(",", "")
    m = re.search(r"\$([0-9.]+)\s+to\s+\$([0-9.]+)", s)
    if m:
        return round(float(m.group(1)) - 0.005, 3), round(float(m.group(2)) + 0.005, 3)
    m = re.search(r"(Above|above|>)\s*\$([0-9.]+)", s)
    if m:
        return round(float(m.group(2)) + 0.005, 3), np.inf
    m = re.search(r"\$([0-9.]+)\s+or\s+(above|higher|more)", s)
    if m:
        return round(float(m.group(1)) - 0.005, 3), np.inf
    m = re.search(r"(Below|below|<)\s*\$([0-9.]+)", s)
    if m:
        return -np.inf, round(float(m.group(2)) - 0.005, 3)
    m = re.search(r"\$([0-9.]+)\s+or\s+(below|lower|less)", s)
    if m:
        return -np.inf, round(float(m.group(1)) + 0.005, 3)
    return None


def load_markets(series: str):
    import pandas as pd
    p = KALSHI / "kalshi_markets" / ("series=%s" % series) / "part.parquet"
    cols = ["ticker", "event_ticker", "yes_sub_title", "strike_type", "floor_strike", "cap_strike", "result", "status",
            "expiration_value_num", "volume_fp", "open_interest_fp", "close_time"]
    have = set(pd.read_parquet(p).columns)
    mk = pd.read_parquet(p, columns=[c for c in cols if c in have])
    for c in cols:
        if c not in mk.columns:
            mk[c] = None
    mk["volume_fp"] = pd.to_numeric(mk["volume_fp"], errors="coerce")
    mk["open_interest_fp"] = pd.to_numeric(mk["open_interest_fp"], errors="coerce")
    return mk


def load_candles(series: str, event_ticker: str):
    """1-minute candles of one event, bid/ask closes in probability units. Returns None if the event has none."""
    import pandas as pd
    p = KALSHI / "kalshi_candles" / "period=1" / ("series=%s" % series) / ("event=%s" % event_ticker) / "part.parquet"
    if not p.exists():
        return None
    c = pd.read_parquet(p, columns=["ts", "ticker", "yes_bid_close", "yes_ask_close", "volume", "open_interest"])
    if c.empty:
        return None
    scale = 100.0 if np.nanmax(c[["yes_bid_close", "yes_ask_close"]].values) > 1.5 else 1.0   # stored in cents
    c["bid"] = c["yes_bid_close"] / scale
    c["ask"] = c["yes_ask_close"] / scale
    c["price_scale"] = scale
    return c


def kalshi_at(candles, ticker: str, snap_utc) -> Optional[Dict[str, Any]]:
    """The bar ending at the snapshot minute (covers (T-60s, T]); else the latest bar ending within the stale limit."""
    import pandas as pd
    if candles is None:
        return None
    t_end = int(pd.Timestamp(snap_utc).ceil("1min").timestamp())
    c = candles[candles["ticker"] == ticker]
    c = c[(c["ts"] <= t_end) & (c["ts"] > t_end - 60 * KALSHI_STALE_MAX_MIN)]
    if c.empty:
        return None
    r = c.sort_values("ts").iloc[-1]
    bid = float(r["bid"]) if r["bid"] == r["bid"] else None
    ask = float(r["ask"]) if r["ask"] == r["ask"] else None
    return {"bid": bid, "ask": ask, "ts": int(r["ts"]), "age_min": (t_end - int(r["ts"])) / 60.0,
            "bar_volume": float(r["volume"]) if r["volume"] == r["volume"] else None,
            "open_interest": float(r["open_interest"]) if r["open_interest"] == r["open_interest"] else None,
            "exact_bar": bool(int(r["ts"]) == t_end)}


# --------------------------------------------------------------------------
# the hedge: outer condor on the $0.50 grid, four legs, OTM side of each strike
# --------------------------------------------------------------------------

def structure_spec(lo_edge: float, hi_edge: float, shift_lo: int = 0, shift_hi: int = 0) -> Dict[str, Any]:
    """The replicating structure in call terms: value = k0 * D + sum(sign * C(K)).
    Bracket [X-0.005, X+0.995): the outer condor C(X-0.5) - C(X) - C(X+1) + C(X+1.5), four legs, k0 = 0.
    Upper tail (X-0.005, inf): the lower spread C(X-0.5) - C(X), two legs.
    Lower tail (-inf, Y-0.005]: 0.5 - [C(Y) - C(Y+0.5)], two legs and k0 = SPREAD_WIDTH of cash.
    Every structure pays SPREAD_WIDTH per bbl inside the bracket and 0 beyond its ramps, which lie outside the bracket.
    Shifts move a spread outward in 0.25 steps when a strike is not quoted (the ramp widens away from the bracket)."""
    s_lo, s_hi = 0.25 * shift_lo, 0.25 * shift_hi
    w = SPREAD_WIDTH
    legs: List[Tuple[float, int]] = []
    k0 = 0.0
    if np.isfinite(lo_edge):
        X = round(lo_edge + 0.005, 2)
        legs += [(round(X - w - s_lo, 2), +1), (round(X - s_lo, 2), -1)]
    if np.isfinite(hi_edge):
        Y = round(hi_edge + 0.005, 2)
        legs += [(round(Y + s_hi, 2), -1), (round(Y + w + s_hi, 2), +1)]
        if not np.isfinite(lo_edge):
            k0 = w
    return {"legs": legs, "k0": k0, "strikes": [k for k, _ in legs]}


def condor_strikes(lo_edge: float, hi_edge: float, shift_lo: int = 0, shift_hi: int = 0) -> List[float]:
    return structure_spec(lo_edge, hi_edge, shift_lo, shift_hi)["strikes"]


def condor_payoff(S, spec) -> np.ndarray:
    """Payoff per bbl of the long structure. `spec` is a structure_spec dict (a bare strike list is the 4-leg condor)."""
    S = np.asarray(S, float)
    if not isinstance(spec, dict):
        spec = {"legs": list(zip(spec, (+1, -1, -1, +1))), "k0": 0.0}
    return spec["k0"] + sum(sg * np.maximum(S - k, 0.0) for k, sg in spec["legs"])


def structure_quotes(raw_q, spec, F0: float, D: float) -> Optional[Dict[str, Any]]:
    """Executable quotes of the legs from the raw TBBO snapshot (last two-sided quote per instrument in the window).
    Each leg is taken on its OTM side (call above the forward, put below, equivalent by parity) and expressed in call
    terms so the structure value is the spec's. Returns None if a leg is unquoted."""
    if not isinstance(spec, dict):
        spec = {"legs": list(zip(spec, (+1, -1, -1, +1))), "k0": 0.0}
    legs = []
    for k, sg in spec["legs"]:
        right = "C" if k >= F0 else "P"
        row = raw_q[(np.isclose(raw_q["strike"].values, k)) & (raw_q["right"].values == right)]
        if row.empty:
            other = raw_q[(np.isclose(raw_q["strike"].values, k)) & (raw_q["right"].values != right)]
            if other.empty:
                return None
            row, right = other, ("P" if right == "C" else "C")
        r = row.iloc[0]
        bid, ask = float(r["bid_px_00"]), float(r["ask_px_00"])
        conv = 0.0 if right == "C" else D * (F0 - k)          # C = P + D (F - K)
        legs.append({"strike": k, "right": right, "sign": sg, "bid": bid, "ask": ask, "hs": 0.5 * (ask - bid),
                     "mid_call": 0.5 * (bid + ask) + conv, "bid_call": bid + conv, "ask_call": ask + conv,
                     "age_min": float(r["age_min"])})
    k0 = spec["k0"] * D
    buy = k0 + sum(l["ask_call"] if l["sign"] > 0 else -l["bid_call"] for l in legs)    # pay to buy the structure
    sell = k0 + sum(l["bid_call"] if l["sign"] > 0 else -l["ask_call"] for l in legs)   # receive to sell it
    mid = k0 + sum(l["sign"] * l["mid_call"] for l in legs)
    return {"legs": legs, "buy": buy, "sell": sell, "mid": mid, "sum_hs": sum(l["hs"] for l in legs), "n_legs": len(legs),
            "max_age_min": max(l["age_min"] for l in legs), "digital_mid": mid / SPREAD_WIDTH}


def find_structure(raw_q, lo_edge: float, hi_edge: float, F0: float, D: float) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], Tuple[int, int]]:
    for shift in range(LEG_SHIFT_MAX + 1):
        for s_lo, s_hi in sorted({(a, b) for a in range(shift + 1) for b in range(shift + 1) if max(a, b) == shift}):
            spec = structure_spec(lo_edge, hi_edge, s_lo, s_hi)
            st = structure_quotes(raw_q, spec, F0, D)
            if st is not None:
                return st, spec, (s_lo, s_hi)
    return None, structure_spec(lo_edge, hi_edge), (0, 0)


def estimate_leg_hs(chain_K: np.ndarray, chain_hs: np.ndarray, strikes: List[float], radius: float = 1.0) -> Optional[float]:
    """Sum over legs of the median synchronised half-spread of the chain's quoted strikes within `radius` dollars of
    the leg (within 2 * radius if none). An ESTIMATE of the CME spread cost, used only for the signal record of
    brackets whose legs were not all quoted in the window - never for a trade (protocol §5, amendment 3)."""
    K = np.asarray(chain_K, float)
    hs = np.asarray(chain_hs, float)
    total = 0.0
    for k in strikes:
        for rad in (radius, 2 * radius):
            near = np.abs(K - k) <= rad + 1e-9
            if near.any():
                total += float(np.median(hs[near]))
                break
        else:
            return None
    return total


# --------------------------------------------------------------------------
# friction (protocol §4)
# --------------------------------------------------------------------------

def kalshi_fee(P: float) -> float:
    return KALSHI_FEE_COEF * P * (1.0 - P)


def cme_fees_per_contract(contracts_per_structure: int = SIZE_APPLICABLE) -> float:
    return 4 * CME_FEE_PER_LEG * (1.0 + CME_EXIT_FRACTION) / contracts_per_structure


def friction(P: float, sum_hs: float, contracts_per_structure: int = SIZE_APPLICABLE) -> Dict[str, float]:
    f_k = kalshi_fee(P)
    f_spread = sum_hs / SPREAD_WIDTH
    f_cme = cme_fees_per_contract(contracts_per_structure)
    return {"kalshi_fee": f_k, "cme_spread": f_spread, "cme_fees": f_cme, "total": f_k + f_spread + f_cme}


# --------------------------------------------------------------------------
# the interior-local-minimum rule (protocol §3)
# --------------------------------------------------------------------------

def trough_regions(s: np.ndarray, f: np.ndarray, dip: float = TROUGH_DIP, floor_frac: float = TROUGH_FLOOR) -> List[Tuple[float, float]]:
    """Intervals of s on which the posterior-mean density sits in an interior trough: around a local minimum with a
    local maximum on each side (both >= floor_frac * max f) and at least `dip` below the lower of them, the region
    where f lies in the lower half of the dip, f < f_min + 0.5 (min(peak_L, peak_R) - f_min)."""
    f = np.asarray(f, float)
    s = np.asarray(s, float)
    n = len(f)
    fmax = f.max()
    if fmax <= 0 or n < 5:
        return []
    peaks = [i for i in range(1, n - 1) if f[i] >= f[i - 1] and f[i] > f[i + 1] and f[i] >= floor_frac * fmax]
    regions: List[Tuple[float, float]] = []
    for a, b in zip(peaks[:-1], peaks[1:]):
        seg = f[a:b + 1]
        i_min = a + int(np.argmin(seg))
        low_peak = min(f[a], f[b])
        if f[i_min] > (1.0 - dip) * low_peak:
            continue
        level = f[i_min] + 0.5 * (low_peak - f[i_min])   # the lower half of the dip
        lo = i_min
        while lo > a and f[lo - 1] < level:
            lo -= 1
        hi = i_min
        while hi < b and f[hi + 1] < level:
            hi += 1
        regions.append((float(s[lo]), float(s[hi])))
    return regions


def overlaps(lo: float, hi: float, regions: List[Tuple[float, float]]) -> bool:
    return any(not (hi <= r0 or lo >= r1) for r0, r1 in regions)


# --------------------------------------------------------------------------
# Stage 16 and 18
# --------------------------------------------------------------------------

def bracket_draws(model, thetas: np.ndarray, edges_lo: np.ndarray, edges_hi: np.ndarray) -> np.ndarray:
    """P(lo < S <= hi) per draw and bracket from the posterior draws, integrating the grid density."""
    s_edges = np.concatenate([[model.s[0]], 0.5 * (model.s[1:] + model.s[:-1]), [model.s[-1]]])
    pts = np.unique(np.concatenate([edges_lo[np.isfinite(edges_lo)], edges_hi[np.isfinite(edges_hi)]]))
    out = np.empty((thetas.shape[0], len(edges_lo)))
    for i in range(thetas.shape[0]):
        p, _ = model.density(thetas[i])
        cum = np.concatenate([[0.0], np.cumsum(p)])
        c = np.interp(pts, s_edges, cum, left=0.0, right=1.0)
        F = dict(zip(pts.tolist(), c.tolist()))
        lo = np.array([F[x] if np.isfinite(x) else 0.0 for x in edges_lo])
        hi = np.array([F[x] if np.isfinite(x) else 1.0 for x in edges_hi])
        out[i] = np.clip(hi - lo, 0.0, 1.0)
    return out


def logit(p):
    p = np.clip(np.asarray(p, float), LOGIT_CLIP, 1.0 - LOGIT_CLIP)
    return np.log(p / (1.0 - p))


def stage18(p_mkt_mid: np.ndarray, pq_draws: np.ndarray, m: np.ndarray) -> Optional[np.ndarray]:
    """Per draw: logit(p_mkt) = a + b logit(p_Q) + c m. Returns (M, 3) of (a, b, c), or None with < 4 brackets."""
    y = logit(p_mkt_mid)
    n = len(y)
    if n < 4:
        return None
    out = np.empty((pq_draws.shape[0], 3))
    ones = np.ones(n)
    for i in range(pq_draws.shape[0]):
        X = np.column_stack([ones, logit(pq_draws[i]), m])
        out[i], *_ = np.linalg.lstsq(X, y, rcond=None)
    return out


def stage18_pooled(blocks: List[Tuple[np.ndarray, np.ndarray, np.ndarray]]) -> Optional[np.ndarray]:
    """Pooled across dates with a per-date intercept, common b and c. blocks = [(p_mkt_mid, pq_draws, m), ...]."""
    blocks = [b for b in blocks if len(b[0]) >= 2]
    if len(blocks) < 2:
        return None
    M = min(b[1].shape[0] for b in blocks)
    y = np.concatenate([logit(b[0]) for b in blocks])
    m = np.concatenate([b[2] for b in blocks])
    D = np.zeros((len(y), len(blocks)))
    k = 0
    for j, b in enumerate(blocks):
        D[k:k + len(b[0]), j] = 1.0
        k += len(b[0])
    out = np.empty((M, 2))
    for i in range(M):
        x = np.concatenate([logit(b[1][i]) for b in blocks])
        X = np.column_stack([D, x, m])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        out[i] = beta[-2:]
    return out


def compare_bracket(b: Dict[str, Any], ctx: Dict[str, Any]) -> None:
    """Stages 17-19 and the P&L for one bracket whose posterior draws and Kalshi bar are already on it. Pure in its inputs,
    so a stored record can be re-processed (python3 -m synth.backtest --reprocess) without re-running the sampler."""
    k = b.get("kalshi")
    F0, D, raw_q, S_T = ctx["F0"], ctx["D"], ctx["raw_q"], ctx["S_T"]
    r = b
    if k is None or k["bid"] is None or k["ask"] is None:
        b["status"] = "no_two_sided_kalshi_quote"
        b["pq_draws"] = None   # keep the pickle small where no comparison exists
        return
    bid, ask = k["bid"], k["ask"]
    b["kalshi_mid"] = 0.5 * (bid + ask)
    b["kalshi_spread"] = ask - bid
    b["g_mid"] = b["kalshi_mid"] - b["pq_mean"]
    # the side is fixed by the mid gap before the executable gap is computed
    if b["g_mid"] > 0:
        b["side"], P = "sell_kalshi", bid          # Kalshi rich: sell the bracket at the bid, buy the structure
    else:
        b["side"], P = "buy_kalshi", ask           # Kalshi cheap: buy at the ask, sell the structure
    b["P_exec"] = P
    b["g"] = P - b["pq_mean"]
    # hedge legs
    fresh = raw_q[raw_q["age_min"] <= LEG_MAX_AGE_MIN] if raw_q is not None else None
    st, spec, shifts = find_structure(fresh, r["lo"], r["hi"], F0, D) if fresh is not None and len(fresh) else (None, structure_spec(r["lo"], r["hi"]), (0, 0))
    st_stale, _, _ = find_structure(raw_q, r["lo"], r["hi"], F0, D) if raw_q is not None and len(raw_q) else (None, None, None)
    b["chain_digital_stale"] = None if st_stale is None else st_stale["digital_mid"]
    b["legs_stale_max_age_min"] = None if st_stale is None else st_stale["max_age_min"]
    ks = spec["strikes"]
    b["legs"] = None if st is None else [{kk: vv for kk, vv in l.items()} for l in st["legs"]]
    b["leg_strikes"], b["leg_shifts"], b["n_legs"] = ks, shifts, len(ks)
    b["structure"] = None if st is None else {kk: vv for kk, vv in st.items() if kk != "legs"}
    b["chain_digital_mid"] = None if st is None else st["digital_mid"]
    fr = friction(P, st["sum_hs"] if st is not None else float("nan"))
    b["friction"] = fr
    # the estimate from the synchronised chain's own half-spreads, for the signal record only
    hs_est = estimate_leg_hs(ctx["chain_K"], ctx["chain_hs"], ks)
    b["friction_est"] = None if hs_est is None else friction(P, hs_est)
    b["excess_est"] = None if hs_est is None else abs(P - b["pq_mean"]) - b["band90"] - b["friction_est"]["total"]
    # Stage 19
    status = None
    if not ctx["date_ok"]:
        status = "date_gated"
    elif P < PRICE_MIN or P > PRICE_MAX or P <= 0.0 or P >= 1.0:
        status = "price_out_of_range"
    elif b["band90"] > BAND_MAX:
        status = "band_too_wide"
    elif b["interior_minimum"]:
        status = "interior_minimum"
    elif st is None:
        status = "cme_leg_unquoted"
    elif abs(b["g"]) <= b["band90"] + fr["total"]:
        status = "below_threshold"
    else:
        status = "traded"
    b["status"] = status
    b["excess"] = abs(b["g"]) - b["band90"] - (fr["total"] if st is not None else float("nan"))
    # signal record: a bracket whose legs were not all quoted, but whose gap would clear band + estimated friction
    b["would_clear_est"] = bool(status == "cme_leg_unquoted" and b["excess_est"] is not None and b["excess_est"] > 0)
    # settlement and P&L (computed for every bracket with a structure, so the untraded signals carry a record too)
    res = (r["result"] or "").lower()
    settled_yes = True if res == "yes" else False if res == "no" else None
    if settled_yes is None and ctx["ice_settle"] is not None:
        settled_yes = bool(r["lo"] < ctx["ice_settle"] <= r["hi"])
        b["result_source"] = "expiration_value"
    else:
        b["result_source"] = "result"
        if ctx["ice_settle"] is not None and settled_yes is not None and settled_yes != bool(r["lo"] < ctx["ice_settle"] <= r["hi"]):
            b["result_mismatch"] = True
    b["settled_yes"] = settled_yes
    if st is not None and S_T is not None and settled_yes is not None:
        s_k = +1 if b["side"] == "buy_kalshi" else -1
        pi_T = float(condor_payoff(S_T, spec))
        pi_exec = st["sell"] if s_k > 0 else st["buy"]        # long Kalshi -> short structure at the sell side
        pnl_k = s_k * ((1.0 if settled_yes else 0.0) - P) - fr["kalshi_fee"]
        pnl_c = -s_k * (pi_T - pi_exec) / SPREAD_WIDTH - fr["cme_fees"]
        b["pnl_per_contract"] = pnl_k + pnl_c
        b["pnl_kalshi"], b["pnl_cme"] = pnl_k, pnl_c
        b["locked_gap"] = s_k * (pi_exec / SPREAD_WIDTH - P) - fr["kalshi_fee"] - fr["cme_fees"]
        mism = pi_T / SPREAD_WIDTH - (1.0 if settled_yes else 0.0)   # structure minus Kalshi payoff, lives in the ramps
        b["ramp_realised"] = -s_k * mism
        b["in_ramp"] = bool(abs(mism) > 1e-9)
        # posterior view of the ramp before the fact
        s_grid = ctx["grid_s"]
        pay = condor_payoff(s_grid, spec) / SPREAD_WIDTH
        ind = ((s_grid > r["lo"]) & (s_grid <= r["hi"])).astype(float)
        mm = pay - ind
        w = np.zeros(s_grid.size)
        h = np.diff(s_grid)
        w[:-1] += 0.5 * h
        w[1:] += 0.5 * h
        p_mean = ctx["f_mean"] * w     # posterior-mean density -> cell masses
        p_mean = p_mean / p_mean.sum()
        b["ramp_prob"] = float(p_mean[np.abs(mm) > 1e-9].sum())
        b["ramp_expected_loss"] = float(np.sum(p_mean * np.maximum(-s_k * mm, 0.0)))
    else:
        b["pnl_per_contract"] = None


def contract_check(d: Dict[str, Any], under: Optional[str], settles: Dict[Tuple[str, str], float], ice_by_date: Dict[str, float]) -> Dict[str, Any]:
    """Gate 0b verified ex post (protocol amendment 4): Kalshi's realised settlement value (the event's own, else the same-day KXWTI
    event's) must equal the NYMEX settlement of the option's underlying to the cent. If it instead equals another month's, the
    contract assignment (usually the calendar fallback) was wrong and the date is a Gate 0b failure, whatever the gaps look like."""
    ice = d.get("ice_settle")
    if ice is None:
        ice = ice_by_date.get(d["settle_date"])
    out = {"ice_ref": ice, "underlying": under, "mismatch": False, "basis_anomaly": False, "reason": None}
    s_under = settles.get((d["settle_date"], under)) if under else None
    out["nymex_under"] = s_under
    if ice is None or s_under is None:
        out["reason"] = "unverifiable: no settlement value on either side"
        return out
    if abs(ice - s_under) <= CONTRACT_TOL:
        return out
    others = sorted((sym, v) for (dt, sym), v in settles.items() if dt == d["settle_date"] and sym != under and abs(v - ice) <= 0.006)
    if others:
        out["mismatch"] = True
        out["reason"] = "Kalshi settled %.2f = NYMEX %s; the option underlying %s settled %.2f (source of the match: %s)" % (ice, others[0][0], under, s_under, d.get("contract_source"))
    else:
        out["basis_anomaly"] = True
        out["reason"] = "Kalshi settled %.2f, NYMEX %s %.2f, no other month matches: unexplained basis %+.2f" % (ice, under, s_under, ice - s_under)
    return out


def reprocess_record(rec: Dict[str, Any], settles: Dict[Tuple[str, str], float], ice_by_date: Dict[str, float]) -> Dict[str, Any]:
    """Re-apply the comparison stage to a stored record (new leg rule, contract check, thresholds); the extraction is untouched."""
    import pandas as pd
    from . import realchain
    x = rec.get("extraction")
    if not x or not x.get("gate0") or rec["outcome"] in ("g0a_no_same_day_expiry", "g0c_too_few_strikes", "g0d_no_intraday_bars", "extraction_error", "no_kalshi_event"):
        return rec
    d = {"settle_date": rec["settle_date"], "ice_settle": rec["ice_settle"], "contract_source": rec.get("contract_source"), "root": rec["root"]}
    rec["contract_check"] = contract_check(d, x.get("underlying"), settles, ice_by_date)
    if x.get("contract_month_match") is False:
        rec["outcome"] = "g0b_contract_mismatch"
        return rec
    p = realchain.DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % rec["root"]) / ("expiry=%s" % rec["settle_date"]) / "part.parquet"
    tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
    snap_ts = pd.Timestamp(rec["snap_time_et"]).tz_localize(realchain.ET)
    raw_q = realchain.snapshot(tb, snap_ts.tz_convert("UTC"), WINDOW_MIN)
    S_T = settles.get((rec["settle_date"], x.get("underlying")))
    rec["nymex_settle"] = S_T
    ctx = {"F0": x["F0"], "D": x["D_used"], "raw_q": raw_q, "S_T": S_T, "ice_settle": rec["ice_settle"], "grid_s": np.asarray(x["act3_grid_s"], float),
           "f_mean": np.asarray(x["act3_grid_f_mean"], float), "chain_K": x["K"], "chain_hs": x["hs"],
           "date_ok": bool(rec.get("sampler_ok") and not rec.get("split_half_fired") and not rec["contract_check"]["mismatch"])}
    for b in rec["brackets"]:
        if b.get("kalshi") is None or b.get("pq_draws") is None:
            continue
        compare_bracket(b, ctx)
    any_price = any(b.get("kalshi_mid") is not None for b in rec["brackets"])
    if not any_price:
        rec["outcome"] = "no_kalshi_candles"
    elif rec["contract_check"]["mismatch"]:
        rec["outcome"] = "g0b_contract_mismatch"
    else:
        rec["outcome"] = ("g4_split_half_fired" if rec.get("split_half_fired") else "sampler_fail" if not rec.get("sampler_ok") else "cleared")
    return rec


# --------------------------------------------------------------------------
# one (date, snapshot)
# --------------------------------------------------------------------------

def run_job(job: Dict[str, Any]) -> Dict[str, Any]:
    import pandas as pd
    from . import act3, realchain
    d, snap, series = job["date"], job["snap"], job["series"]
    rec: Dict[str, Any] = {"series": series, "settle_date": d["settle_date"], "snap": snap, "event_ticker": d["event_ticker"],
                           "root": d["root"], "cl_contract": d["cl_contract"], "contract_source": d.get("contract_source"),
                           "ice_settle": d["ice_settle"], "error": None, "outcome": None, "brackets": []}
    t0 = time.time()
    try:
        if d["root"] is None:
            rec["outcome"] = "g0a_no_same_day_expiry"
            return rec
        # --- the frozen extractor -------------------------------------------------------------------------
        x = realchain.run_one(dict(job, arm=ARM, window=WINDOW_MIN, keep_thetas=True))
        rec["extraction"] = {k: v for k, v in x.items() if k not in ("act3_thetas", "act2_grid")}
        if x.get("error"):
            rec["outcome"] = "extraction_error"
            rec["error"] = x["error"]
            return rec
        if not x.get("gate0"):
            reason = x.get("gate0_reason", "")
            rec["outcome"] = ("g0d_no_intraday_bars" if "intraday" in reason else
                              "g0c_too_few_strikes" if ("strikes" in reason or "quotes" in reason or "parity" in reason) else "g0c_too_few_strikes")
            rec["gate0_reason"] = reason
            return rec
        if x.get("contract_month_match") is False:
            rec["outcome"] = "g0b_contract_mismatch"
            return rec
        F0, D, T = x["F0"], x["D_used"], x["T_years"]
        split_fired = bool(x["split_half"]["fired"])
        sampler_ok = bool(x["checks"]["sampler_bracket_ok"])
        rec["split_half_fired"] = split_fired
        rec["sampler_ok"] = sampler_ok
        rec["act2_fired"] = bool(x["act2_signal"]["fired"])
        rec["act2_cents"] = x["act2_signal"]["cents"]
        rec["loo_flagged_strikes"] = list(x["loo"]["flagged_strikes"])
        rec["chi2_per_strike"] = x["act3_chi2_per_strike"]
        rec["forward_source"] = x.get("forward_source")
        rec["F0"] = F0
        rec["meanF_minus_F0_cents"] = x["act3u_meanF_mean"] * 100.0 - 100.0 * F0
        rec["real_path"] = x.get("real_path")
        # --- Kalshi side ---------------------------------------------------------------------------------
        mk = job["markets"][job["markets"]["event_ticker"] == d["event_ticker"]]
        if mk.empty:
            rec["outcome"] = "no_kalshi_event"
            return rec
        candles = load_candles(series, d["event_ticker"])
        snap_ts = realchain.snapshot_times(d["settle_ts"])[snap]
        snap_utc = snap_ts.tz_convert("UTC")
        rec["snap_time_et"] = snap_ts.strftime("%Y-%m-%d %H:%M")
        # edges, verified against the sub-title
        rows = []
        for r in mk.itertuples():
            try:
                lo, hi = market_edges(r.strike_type, r.floor_strike, r.cap_strike)
            except ValueError as exc:
                rows.append({"ticker": r.ticker, "status": "edge_unparsed", "note": repr(exc)})
                continue
            alt = edges_from_subtitle(str(r.yes_sub_title or ""))
            edge_note = None
            if alt is not None and (not np.isclose(alt[0], lo, equal_nan=True) or not np.isclose(alt[1], hi, equal_nan=True)):
                edge_note = "sub-title %s gives (%s, %s) vs fields (%s, %s); sub-title used" % (r.yes_sub_title, alt[0], alt[1], lo, hi)
                lo, hi = alt
            rows.append({"ticker": r.ticker, "sub_title": r.yes_sub_title, "strike_type": r.strike_type, "lo": lo, "hi": hi,
                         "result": r.result, "lifetime_volume": r.volume_fp, "lifetime_oi": r.open_interest_fp, "edge_note": edge_note})
        rows = [r for r in rows if "lo" in r]
        if not rows:
            rec["outcome"] = "no_kalshi_event"
            return rec
        rows.sort(key=lambda r: (r["lo"], r["hi"]))
        # Stage 16: every draw over the exact edges
        a = x["act3_model_args"]
        act3.set_prior(a["prior"], a["nu"], a["m"], hs_floor=a["hs_floor"], hs_mode=a["hs_mode"])
        model = act3.Model(x["K"], x["right"], x["mid"], x["hs"], F0, D, T, a["atm_sigma"], se_F0=a["se_F0"], martingale=True)
        thetas = x["act3_thetas"]
        lo_e = np.array([r["lo"] for r in rows])
        hi_e = np.array([r["hi"] for r in rows])
        pq = bracket_draws(model, thetas, lo_e, hi_e)                        # (M, n_brackets)
        rec["n_draws"] = int(pq.shape[0])
        troughs = trough_regions(x["act3_grid_s"], x["act3_grid_f_mean"])
        rec["trough_regions"] = troughs
        rec["n_modes_mean_density"] = x["act3_n_modes"]
        # raw TBBO snapshot for the executable legs
        p = realchain.DATA_CME / "options_tbbo_by_expiry" / ("root=%s" % d["root"]) / ("expiry=%s" % d["settle_date"]) / "part.parquet"
        tb = pd.read_parquet(p, columns=["ts_event", "instrument_id", "bid_px_00", "ask_px_00", "strike", "right"])
        raw_q = realchain.snapshot(tb, snap_utc, WINDOW_MIN)
        S_T = job["settles"].get((d["settle_date"], x["underlying"]))        # NYMEX settlement of the option's underlying
        rec["nymex_settle"] = S_T
        loo_flags = np.array(x["loo"]["flagged_strikes"], float) if x["loo"]["flagged_strikes"] else np.array([])
        rec["contract_check"] = contract_check(d, x["underlying"], job["settles"], job.get("ice_by_date") or {})
        ctx = {"F0": F0, "D": D, "raw_q": raw_q, "S_T": S_T, "ice_settle": d["ice_settle"], "grid_s": np.asarray(x["act3_grid_s"], float),
               "f_mean": np.asarray(x["act3_grid_f_mean"], float), "chain_K": x["K"], "chain_hs": x["hs"],
               "date_ok": bool(sampler_ok and not split_fired and not rec["contract_check"]["mismatch"])}
        for j, r in enumerate(rows):
            b: Dict[str, Any] = dict(r)
            b.update({"idx": j, "mid_dollar": (0.5 * (r["lo"] + r["hi"])) if np.isfinite(r["lo"]) and np.isfinite(r["hi"]) else None,
                      "pq_mean": float(pq[:, j].mean()), "pq_q05": float(np.percentile(pq[:, j], 5)), "pq_q50": float(np.percentile(pq[:, j], 50)),
                      "pq_q95": float(np.percentile(pq[:, j], 95)), "pq_draws": pq[:, j].astype(np.float32)})
            b["band90"] = b["pq_q95"] - b["pq_q05"]
            b["interior_minimum"] = overlaps(r["lo"], r["hi"], troughs)
            near = [float(k) for k in loo_flags if (np.isfinite(r["lo"]) and abs(k - r["lo"]) <= LOO_NEAR_EDGE) or (np.isfinite(r["hi"]) and abs(k - r["hi"]) <= LOO_NEAR_EDGE)]
            b["loo_near_edge"] = bool(near)
            b["loo_near_strikes"] = near
            k = kalshi_at(candles, r["ticker"], snap_utc)
            b["kalshi"] = k
            compare_bracket(b, ctx)
            rec["brackets"].append(b)
        any_price = any(b.get("kalshi_mid") is not None for b in rec["brackets"])
        if not any_price:
            rec["outcome"] = "no_kalshi_candles"
            return rec
        rec["outcome"] = ("g0b_contract_mismatch" if rec["contract_check"]["mismatch"] else
                          "g4_split_half_fired" if split_fired else "sampler_fail" if not sampler_ok else "cleared")
        # Stage 18 per date (mid-based, two-sided quotes with mid in [1c, 99c])
        ok = [b for b in rec["brackets"] if b.get("kalshi_mid") is not None and STAGE18_MID_MIN <= b["kalshi_mid"] <= STAGE18_MID_MAX
              and b.get("mid_dollar") is not None]
        if len(ok) >= 4:
            abc = stage18(np.array([b["kalshi_mid"] for b in ok]), np.stack([b["pq_draws"] for b in ok], axis=1).astype(float),
                          np.array([b["mid_dollar"] - F0 for b in ok]))
            rec["stage18"] = None if abc is None else {"q05": np.percentile(abc, 5, axis=0).tolist(), "q50": np.percentile(abc, 50, axis=0).tolist(),
                                                       "q95": np.percentile(abc, 95, axis=0).tolist(), "n": len(ok)}
        else:
            rec["stage18"] = None
    except Exception as exc:
        import traceback
        rec["error"] = repr(exc)
        rec["traceback"] = traceback.format_exc()
        rec["outcome"] = "extraction_error"
    rec["seconds"] = time.time() - t0
    return rec


# --------------------------------------------------------------------------
# driver: resumable, one checkpoint per job
# --------------------------------------------------------------------------

def runs_path(series: str) -> Path:
    return RESULTS / ("runs_%s.pkl" % series)


def _key(r: Dict[str, Any]) -> Tuple[str, str]:
    return (r["settle_date"], r["snap"])


def _dump(obj, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(obj, fh)
    os.replace(tmp, path)


def run(series: str, snaps: List[str], workers: int, only: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    from . import realchain
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = runs_path(series)
    have: List[Dict[str, Any]] = pickle.load(open(path, "rb")) if path.exists() else []
    done = {_key(r) for r in have if r.get("error") is None}
    inp = realchain.load_inputs(series=series, clears_only=False)
    markets = load_markets(series)
    ice_by_date = ice_values()
    log("series %s: %d Kalshi events with a settlement since 2026-01-01; %d with a CME expiry on disk; markets table %d rows"
        % (series, len(inp["dates"]), sum(d["root"] is not None for d in inp["dates"]), len(markets)))
    log("FIRST KALSHI PRICE READ happens in the jobs below (protocol §8); protocol commit precedes this log line")
    jobs = [{"date": d, "snap": s, "series": series, "underlying": inp["underlying"], "settles": inp["settles"], "intraday": inp["intraday"],
             "markets": markets, "ice_by_date": ice_by_date}
            for d in inp["dates"] for s in snaps if (only is None or d["settle_date"] in only) and (d["settle_date"], s) not in done]
    log("jobs to run: %d (done %d)" % (len(jobs), len(done)))
    results = [r for r in have if _key(r) in done]
    if jobs:
        ctx = mp.get_context("fork")
        t0 = time.time()
        with ctx.Pool(workers) as pool:
            for i, r in enumerate(pool.imap_unordered(run_job, jobs), 1):
                results.append(r)
                n_tr = sum(1 for b in r["brackets"] if b.get("status") == "traded")
                log("  %3d/%d %s %s %-24s brackets %2d traded %d %5.0fs%s" % (i, len(jobs), r["settle_date"], r["snap"], r["outcome"],
                                                                             len(r["brackets"]), n_tr, time.time() - t0,
                                                                             ("  ERR " + (r.get("error") or "")[:120]) if r.get("error") else ""))
                _dump(results, path)
    _dump(results, path)
    write_logs(series, results)
    return results


def ice_values() -> Dict[str, float]:
    """Kalshi's realised ICE settlement by date, from every WTI event (the weekly's own value is missing on some events;
    the same-day daily event carries the same number)."""
    sys.path.insert(0, str(ROOT))
    import db_common as dc
    ev = dc.kalshi_settlements(series=("KXWTIW", "KXWTI"))
    out: Dict[str, float] = {}
    for r in ev.itertuples():
        if r.expiration_value == r.expiration_value and str(r.settle_date) not in out:
            out[str(r.settle_date)] = float(r.expiration_value)
    return out


def reprocess(series: str) -> List[Dict[str, Any]]:
    from . import realchain
    path = runs_path(series)
    rs = pickle.load(open(path, "rb"))
    inp = realchain.load_inputs(series=series, clears_only=False)
    ice_by_date = ice_values()
    log("reprocess %s: %d records (leg age <= %.0f min, contract check)" % (series, len(rs), LEG_MAX_AGE_MIN))
    out = [reprocess_record(r, inp["settles"], ice_by_date) for r in rs]
    _dump(out, path)
    write_logs(series, out)
    n_mm = sum(1 for r in out if r["outcome"] == "g0b_contract_mismatch")
    log("reprocess %s done: %d contract mismatches, %d traded brackets" % (series, n_mm, sum(1 for r in out for b in r["brackets"] if b.get("status") == "traded")))
    return out


def write_logs(series: str, results: List[Dict[str, Any]]) -> None:
    """The denominator and the bracket log, every row with its reason."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / ("denominator_%s.csv" % series), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["settle_date", "snap", "event_ticker", "outcome", "reason", "n_brackets", "n_two_sided", "n_traded", "split_half_fired", "sampler_ok", "chi2_per_strike"])
        for r in sorted(results, key=lambda r: (r["settle_date"], r["snap"])):
            w.writerow([r["settle_date"], r["snap"], r["event_ticker"], r["outcome"], (r.get("gate0_reason") or r.get("error") or "")[:160],
                        len(r["brackets"]), sum(1 for b in r["brackets"] if b.get("kalshi_mid") is not None),
                        sum(1 for b in r["brackets"] if b.get("status") == "traded"), r.get("split_half_fired"), r.get("sampler_ok"),
                        "" if r.get("chi2_per_strike") is None else "%.2f" % r["chi2_per_strike"]])
    with open(RESULTS / ("brackets_%s.csv" % series), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["settle_date", "snap", "ticker", "lo", "hi", "status", "side", "P_exec", "kalshi_bid", "kalshi_ask", "kalshi_age_min", "pq_mean", "pq_q05", "pq_q95",
                    "band90", "g", "friction_total", "kalshi_fee", "cme_spread", "cme_fees", "excess", "interior_minimum", "loo_near_edge", "chain_digital_mid",
                    "settled_yes", "pnl_per_contract", "locked_gap", "in_ramp", "ramp_prob", "bar_volume", "open_interest", "lifetime_volume", "leg_shifts", "edge_note",
                    "n_legs", "friction_est_total", "excess_est", "would_clear_est"])
        for r in sorted(results, key=lambda r: (r["settle_date"], r["snap"])):
            for b in r["brackets"]:
                k = b.get("kalshi") or {}
                fr = b.get("friction") or {}
                w.writerow([r["settle_date"], r["snap"], b["ticker"], b["lo"], b["hi"], b.get("status"), b.get("side"), b.get("P_exec"), k.get("bid"), k.get("ask"),
                            k.get("age_min"), b.get("pq_mean"), b.get("pq_q05"), b.get("pq_q95"), b.get("band90"), b.get("g"), fr.get("total"), fr.get("kalshi_fee"),
                            fr.get("cme_spread"), fr.get("cme_fees"), b.get("excess"), b.get("interior_minimum"), b.get("loo_near_edge"), b.get("chain_digital_mid"),
                            b.get("settled_yes"), b.get("pnl_per_contract"), b.get("locked_gap"), b.get("in_ramp"), b.get("ramp_prob"), k.get("bar_volume"),
                            k.get("open_interest"), b.get("lifetime_volume"), b.get("leg_shifts"), b.get("edge_note"),
                            b.get("n_legs"), (b.get("friction_est") or {}).get("total"), b.get("excess_est"), b.get("would_clear_est")])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXWTIW")
    ap.add_argument("--snap", default=",".join(SNAPS))
    ap.add_argument("--only", default=None, help="comma-separated settle dates")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--reprocess", action="store_true", help="re-apply the comparison stage to the stored extractions")
    a = ap.parse_args(argv)
    if a.reprocess:
        reprocess(a.series)
    elif not a.report:
        run(a.series, [s.strip() for s in a.snap.split(",")], a.workers, [x.strip() for x in a.only.split(",")] if a.only else None)
    from . import report_backtest
    report_backtest.main([])
    return 0


if __name__ == "__main__":
    sys.exit(main())
