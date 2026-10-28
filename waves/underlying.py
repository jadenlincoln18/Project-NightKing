"""Does the ladder lag its underlying? (brief: NightKing/HANDOFF_underlying_lag.md)

Per ladder with a matched underlying minute path:
  - grid: ladder.store.build_grid (mids, carried forward); U[t] = underlying price at the
    end of the Kalshi bar. CL: bbo-1m quote mid sampled at the minute boundary (ts_recv == T)
    and ohlcv-1m close of the bar ending at T (ts_event == T - 60). ETH-USD: Coinbase candle
    close of the bar starting at T - 60.
  - contract: Kalshi names it (rules text > custom_strike.front_month_contract > Kalshi's
    calendar convention, the V3 logic in wti_arb/db_common) per event; the futures file of
    that contract is the path. No coverage -> the ladder is skipped and counted.
  - implied forward F[t]: the strike at which the ladder's P(>X) (from mids, spread <= 10c)
    crosses 0.5, linearly interpolated; for range ladders P(>X) is the cumulative sum of the
    bracket mids above X. NaN unless the crossing is bracketed by two quoted strikes.
  - Q1: cross-correlation of dF[t] with dU[t - L] for L in -LAGS..+LAGS (positive L = ladder
    lags the underlying), accumulated as sums so ladders pool by addition; also on the
    at-the-money bracket's mid change and on 5-minute changes.
  - beta_j: each bracket's sensitivity dM_j/dU from an OLS through the origin of its minute
    changes on dU over the ladder's matched minutes (>= min_beta_n minutes with dU != 0),
    with the R^2 of that fit.
  - Q2/Q3: for every wave event of the ladder (from waves/results/events.parquet) the
    neighbour's stored response resp_k(h) is decomposed into
        predicted_k(h) = beta_{i+k} * (U[t+h] - U[t-1]) / d
        residual_k(h)  = resp_k(h) - predicted_k(h)
    and the initiator's own move d into beta_i * (U[t] - U[t-1]) (the underlying's share).
Everything is a description; nothing is a trading rule.
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ladder import store

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "wti_arb"))
import db_common as dc  # noqa: E402  (contract mapping only; no network, no key)

CME = ROOT / "data_cme" / "parquet" / "futures_intraday"
CRYPTO = ROOT / "waves_data" / "crypto"
LAGS = 10
HORIZONS = (0, 1, 2, 5, 10, 30)
K = 5
SPREAD_CAP = 10.0
MIN_BETA_N = 100
ETH_SERIES = ("KXETH",)
WTI_SERIES = ("KXWTI", "KXWTIW", "KXWTIMAX", "KXWTIMIN", "KXWTIMAXM", "KXWTIMINM")

_cache = {}


def load_cl(symbol):
    """Minute series for one CL contract: index = Kalshi bar-end epoch (s); columns mid (bbo), close (ohlcv)."""
    if symbol in _cache:
        return _cache[symbol]
    fb = CME / "schema=bbo-1m" / ("symbol=%s" % symbol) / "part.parquet"
    fo = CME / "schema=ohlcv-1m" / ("symbol=%s" % symbol) / "part.parquet"
    out = None
    if fb.exists():
        b = pd.read_parquet(fb, columns=["ts_recv", "bid_px_00", "ask_px_00"])
        b["ts"] = (b.ts_recv.astype("int64") // 10 ** 9)
        b["ts"] = ((b.ts + 30) // 60) * 60  # the sample at the boundary; snap to the minute
        b = b[(b.bid_px_00 > 0) & (b.ask_px_00 > 0)]
        out = b.groupby("ts").agg(mid=("bid_px_00", "last"), ask=("ask_px_00", "last"))
        out["mid"] = (out["mid"] + out["ask"]) / 2.0
        out = out[["mid"]]
    if fo.exists():
        o = pd.read_parquet(fo, columns=["ts_event", "close"])
        o["ts"] = (o.ts_event.astype("int64") // 10 ** 9) + 60  # bar [T-60, T) -> Kalshi bar ending T
        oc = o.groupby("ts").close.last()
        out = oc.to_frame("close") if out is None else out.join(oc.to_frame("close"), how="outer")
    _cache[symbol] = out
    return out


def load_eth():
    if "ETH" in _cache:
        return _cache["ETH"]
    f = CRYPTO / "ETH-USD_1m.parquet"
    if not f.exists():
        _cache["ETH"] = None
        return None
    c = pd.read_parquet(f, columns=["ts", "close"])
    c["ts"] = c.ts.astype("int64") + 60  # candle starts at ts -> Kalshi bar ending ts + 60
    out = c.groupby("ts").close.last().to_frame("mid")
    out["close"] = out["mid"]
    _cache["ETH"] = out
    return out


def contract_for(markets_rows):
    """Kalshi-named CL contract for one event (rules > named > calendar), as in V3."""
    rules = next((r for r in markets_rows.get("rules_primary", pd.Series(dtype=object)) if isinstance(r, str)), None)
    named = next((r for r in markets_rows.get("custom_strike.front_month_contract", pd.Series(dtype=object)) if isinstance(r, str)), None)
    c = dc.rules_contract(rules) or dc.kalshi_front_month_to_cl(named)
    src = "rules" if dc.rules_contract(rules) else ("named" if c else None)
    if c is None:
        close = pd.to_datetime(int(markets_rows.close_time_epoch.min()), unit="s", utc=True).tz_convert(dc.ET).date()
        c, src = dc.kalshi_calendar_contract(close), "calendar"
    return c, src


def underlying_for(g, markets_rows):
    """(U DataFrame aligned to g.ts, contract, source) or (None, ...) when there is no coverage."""
    if g.series in ETH_SERIES:
        u = load_eth(); c, src = "ETH-USD", "coinbase"
    elif g.series in WTI_SERIES:
        c, src = contract_for(markets_rows)
        u = load_cl(c)
    else:
        return None, None, None
    if u is None:
        return None, c, src
    u = u.reindex(g.ts)
    if u["mid"].notna().mean() < 0.5:
        return None, c, src
    return u, c, src


def implied_forward(g, spread_cap=SPREAD_CAP):
    """F[t]: strike where P(>X) crosses 0.5 (linear), NaN when not bracketed. Also the ATM column index per minute."""
    mid, sp = g.mid, g.spread
    n, m = mid.shape
    q = ~np.isnan(mid) & (sp <= spread_cap)
    if g.kind == "cumul":
        P = np.where(q, mid, np.nan) / 100.0
        X = g.strikes
    else:
        # range ladder: brackets ordered lower tail, body by floor, upper tail; P(>X_i) for the i-th boundary
        pr = np.where(q, mid, np.nan) / 100.0
        # cumulative from the top: P(> floor of bracket i) = sum of bracket probs i..m-1
        P = np.full((n, m), np.nan)
        ok_all = ~np.isnan(pr).any(axis=1)
        cs = np.cumsum(pr[:, ::-1], axis=1)[:, ::-1]
        P[ok_all] = cs[ok_all]
        X = g.strikes
    F = np.full(n, np.nan); atm = np.full(n, -1, dtype=int)
    above = P >= 0.5
    for t in range(n):
        row = P[t]; ok = ~np.isnan(row)
        if ok.sum() < 2:
            continue
        idx = np.flatnonzero(ok)
        pv = row[idx]
        # P should be non-increasing in X; find the last index with P >= 0.5 and the next with P < 0.5
        hi = np.flatnonzero(pv >= 0.5); lo = np.flatnonzero(pv < 0.5)
        if hi.size == 0 or lo.size == 0:
            continue
        a = hi[-1]; b = lo[lo > a]
        if b.size == 0:
            continue
        b = b[0]
        xa, xb, pa, pb = X[idx[a]], X[idx[b]], pv[a], pv[b]
        F[t] = xa + (pa - 0.5) / (pa - pb) * (xb - xa) if pa != pb else xa
        atm[t] = idx[a] if abs(pa - 0.5) <= abs(pb - 0.5) else idx[b]
    return F, atm


def xcorr_sums(x, y, lags=LAGS):
    """Accumulators for corr(x[t], y[t-L]) over L in -lags..lags: n, sum x, sum y, sum xx, sum yy, sum xy per lag."""
    out = {}
    for L in range(-lags, lags + 1):
        if L >= 0:
            a, b = x[L:], y[:len(y) - L] if L else y
        else:
            a, b = x[:L], y[-L:]
        ok = ~np.isnan(a) & ~np.isnan(b)
        a, b = a[ok], b[ok]
        out[L] = np.array([ok.sum(), a.sum(), b.sum(), (a * a).sum(), (b * b).sum(), (a * b).sum()])
    return out


def corr_from_sums(v):
    n, sx, sy, sxx, syy, sxy = v
    if n < 3:
        return np.nan
    cx = sxx - sx * sx / n; cy = syy - sy * sy / n
    return (sxy - sx * sy / n) / np.sqrt(cx * cy) if cx > 0 and cy > 0 else np.nan


def betas(g, dU, min_n=MIN_BETA_N):
    mid, sp = g.mid, g.spread
    n, m = mid.shape
    valid = ~np.isnan(mid) & (sp <= SPREAD_CAP)
    dM = np.full((n, m), np.nan); dM[1:] = mid[1:] - mid[:-1]
    dM[~(valid & np.roll(valid, 1, axis=0))] = np.nan; dM[0] = np.nan
    beta = np.full(m, np.nan); r2 = np.full(m, np.nan); nn = np.zeros(m, dtype=int)
    for j in range(m):
        ok = ~np.isnan(dM[:, j]) & ~np.isnan(dU) & (dU != 0)
        nn[j] = ok.sum()
        if nn[j] < min_n:
            continue
        x, y = dU[ok], dM[ok, j]
        sxx = (x * x).sum()
        if sxx <= 0:
            continue
        b = (x * y).sum() / sxx
        beta[j] = b
        ss = (y * y).sum()
        r2[j] = 1 - ((y - b * x) ** 2).sum() / ss if ss > 0 else np.nan
    return beta, r2, nn


def shape_beta(g, t, spread_cap=SPREAD_CAP):
    """Model-free sensitivity of every bracket's mid (cents) to a $1 rise of the underlying, read
    off the ladder's own shape at minute t: f(X) = -dP(>X)/dX (the implied density, central
    difference on quoted strikes). Cumulative bracket j: beta = f(X_j). Range bracket [a, b):
    beta = f(a) - f(b). Unbiased by quote sparsity, unlike the minute regression."""
    mid, sp = g.mid[t], g.spread[t]
    m = mid.shape[0]
    q = ~np.isnan(mid) & (sp <= spread_cap)
    X = g.strikes
    if g.kind == "cumul":
        P = np.where(q, mid, np.nan)
        idx = np.flatnonzero(q)
        f = np.full(m, np.nan)
        for a, j in enumerate(idx):
            lo = idx[a - 1] if a > 0 else None; hi = idx[a + 1] if a + 1 < idx.size else None
            if lo is not None and hi is not None and X[hi] != X[lo]:
                f[j] = (P[lo] - P[hi]) / (X[hi] - X[lo])
            elif lo is not None and X[j] != X[lo]:
                f[j] = (P[lo] - P[j]) / (X[j] - X[lo])
            elif hi is not None and X[hi] != X[j]:
                f[j] = (P[j] - P[hi]) / (X[hi] - X[j])
        return f
    # range: boundaries X[0] (lower tail cap), X[1..m-1] floors; bracket probs -> cumulative P(> boundary)
    if not q.all():
        return np.full(m, np.nan)
    pr = mid
    P = np.cumsum(pr[::-1])[::-1]  # P(> X_i) for i-th boundary (bracket i and above)
    f = np.full(m, np.nan)
    bnd = X
    dens = np.full(m, np.nan)
    for i in range(1, m - 1):
        if bnd[i + 1] != bnd[i - 1]:
            dens[i] = (P[i - 1] - P[i + 1]) / (bnd[i + 1] - bnd[i - 1])
    for j in range(m):
        lo = dens[j] if j >= 1 else 0.0
        hi = dens[j + 1] if j + 1 < m else 0.0
        if not (np.isnan(lo) or np.isnan(hi)):
            f[j] = lo - hi
    return f


def analyse(g, u, events):
    """Returns (summary dict, event-level DataFrame) for one ladder."""
    n, m = g.mid.shape
    U = u["mid"].values.astype(float)
    Uc = u["close"].values.astype(float) if "close" in u else U
    dU = np.full(n, np.nan); dU[1:] = U[1:] - U[:-1]
    dUc = np.full(n, np.nan); dUc[1:] = Uc[1:] - Uc[:-1]
    F, atm = implied_forward(g)
    dF = np.full(n, np.nan); dF[1:] = F[1:] - F[:-1]
    # ATM bracket mid change, sign-flipped so that up in the underlying is up: for P(>X) ladders dM has the same sign
    dA = np.full(n, np.nan)
    for t in range(1, n):
        j = atm[t - 1]
        if j >= 0 and atm[t] == j:
            dA[t] = g.mid[t, j] - g.mid[t - 1, j]
    s = dict(series=g.series, event=g.event, kind=g.kind, minutes=n, brackets=m,
             matched_minutes=int((~np.isnan(U)).sum()), forward_minutes=int((~np.isnan(F)).sum()),
             fwd_change_minutes=int((~np.isnan(dF) & (dF != 0)).sum()), u_change_minutes=int((~np.isnan(dU) & (dU != 0)).sum()),
             fwd_u_corr0=np.nan)
    s["xc_fwd"] = xcorr_sums(dF, dU); s["xc_atm"] = xcorr_sums(dA, dU); s["xc_fwd_close"] = xcorr_sums(dF, dUc)
    # 5-minute changes
    F5 = F[::5]; U5 = U[::5]
    s["xc_fwd5"] = xcorr_sums(np.diff(F5, prepend=np.nan), np.diff(U5, prepend=np.nan), lags=6)
    s["fwd_u_corr0"] = corr_from_sums(s["xc_fwd"][0])
    beta, r2, nn = betas(g, dU)
    s["beta_median"] = float(np.nanmedian(beta)) if np.isfinite(beta).any() else np.nan
    s["beta_r2_median"] = float(np.nanmedian(r2)) if np.isfinite(r2).any() else np.nan
    s["brackets_with_beta"] = int(np.isfinite(beta).sum())
    rows = []
    if events is not None and len(events):
        ts_index = {int(t): i for i, t in enumerate(g.ts)}
        for _, e in events.iterrows():
            t = ts_index.get(int(e.ts)); i = int(e.i)
            if t is None or t < 1:
                continue
            d = float(e.d)
            r = dict(series=g.series, event=g.event, kind=g.kind, ts=int(e.ts), i=i, d=d, band=float(e.band), weight=float(e.weight),
                     oi=float(e.oi), min_to_close=float(e.min_to_close), spread0=float(e.spread0), vol=float(e.vol),
                     beta_i=beta[i], r2_i=r2[i], du0=U[t] - U[t - 1] if not (np.isnan(U[t]) or np.isnan(U[t - 1])) else np.nan)
            r["pred_d"] = beta[i] * r["du0"] / d if np.isfinite(beta[i]) and np.isfinite(r["du0"]) else np.nan
            sb = shape_beta(g, t - 1)
            r["sbeta_i"] = sb[i]
            r["u_t"] = U[t]
            r["strike_i"] = float(g.strikes[i])
            r["spred_d"] = sb[i] * r["du0"] / d if np.isfinite(sb[i]) and np.isfinite(r["du0"]) else np.nan
            for k in [kk for sgn in (1, -1) for kk in (sgn * np.arange(1, K + 1))]:
                j = i + k
                for h in HORIZONS:
                    key = "resp_%+d_%d" % (k, h)
                    resp = float(e[key]) if key in e and e[key] == e[key] else np.nan
                    th = t + h
                    if 0 <= j < m and th < n and np.isfinite(beta[j]) and not np.isnan(U[th]) and not np.isnan(U[t - 1]):
                        pred = beta[j] * (U[th] - U[t - 1]) / d
                    else:
                        pred = np.nan
                    if 0 <= j < m and th < n and np.isfinite(sb[j]) and not np.isnan(U[th]) and not np.isnan(U[t - 1]):
                        spred = sb[j] * (U[th] - U[t - 1]) / d
                    else:
                        spred = np.nan
                    r["resp_%+d_%d" % (k, h)] = resp
                    r["pred_%+d_%d" % (k, h)] = pred
                    r["spred_%+d_%d" % (k, h)] = spred
                # where the neighbour's strike sits relative to the underlying at t: +1 above, -1 below (cumulative ladders)
                r["side_%+d" % k] = (1.0 if g.strikes[j] > U[t] else -1.0) if (0 <= j < m and not np.isnan(U[t])) else np.nan
            rows.append(r)
    return s, pd.DataFrame(rows)
