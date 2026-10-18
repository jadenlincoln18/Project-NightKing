"""Wave census on one ladder's minute grid (brief sections 1-2). Descriptive only.

Movement is measured on MIDS of the carried-forward grid (ladder.store.build_grid),
restricted to minutes where the bracket is two-sided with spread <= spread_cap on
both the minute and the one before (so the mid means something). A bracket's
minute-to-minute change D is non-zero only on minutes where it printed a candle
(the store is sparse by design: no candle = no change).

Per-bracket normalisation: the empirical distribution of |D| over that bracket's
own NON-ZERO changes. Thresholds q_p are its 90th / 95th / 99th / 99.9th
percentiles. A bracket with fewer than `min_changes` non-zero changes borrows the
ladder's pooled distribution (flagged `fallback`); if the ladder has fewer than
`min_changes` too, the ladder is skipped as a source of events.

An EVENT is (t, i) with |D[t, i]| >= q_90(i). Its `band` is the highest
percentile it clears (90, 95, 99, 99.9). Every event carries:
  - the neighbour response at distance k = +-1..K for horizons h:
        resp_k(h) = (mid[t+h, i+k] - mid[t-1, i+k]) / D[t, i]
    (NaN if the neighbour is not two-sided+tight at t-1, or missing at t+h)
  - the neighbour's first-move minute: smallest h in 0..30 at which its mid differs
    from mid[t-1]; 99 = no move within 30 minutes
  - the initiator's retention ret(h) = (mid[t+h, i] - mid[t-1, i]) / D[t, i]
  - the neighbour's unconditional change rate (changes per valid minute), so the
    first-move timing can be compared with what the neighbour does anyway
  - conditioning: time to close, hour, spread before/after, mid before (moneyness),
    volume in the minute (trade-driven or quote-driven), open interest, position.

Sampling: events in the 90-95 band are kept 1-in-`sub` with weight = sub so the
table stays small; every event >= 95 is kept with weight 1. Counts per band per
ladder are also returned in full (unsampled) for the frequency table.
"""
import numpy as np
import pandas as pd

PCTS = (90.0, 95.0, 99.0, 99.9)
HORIZONS = (0, 1, 2, 5, 10, 30)
RET_H = (1, 2, 5, 10, 30)
K = 5
FIRST_MAX = 30
NONE = 99


def thresholds(absd, pcts=PCTS):
    return np.percentile(absd, pcts) if absd.size else np.full(len(pcts), np.nan)


def census(g, spread_cap=10.0, min_changes=50, sub=4, rng=None):
    rng = rng or np.random.default_rng(0)
    mid, sp = g.mid, g.spread
    n, m = mid.shape
    valid = ~np.isnan(mid) & (sp <= spread_cap)
    D = np.full((n, m), np.nan, dtype=np.float32)
    D[1:] = mid[1:] - mid[:-1]
    D[~(valid & np.roll(valid, 1, axis=0))] = np.nan
    D[0] = np.nan
    absD = np.abs(D)
    nz = np.nan_to_num(absD) >= 0.5
    n_changes = nz.sum(axis=0)
    valid_min = np.maximum(valid.sum(axis=0), 1)
    rate = n_changes / valid_min  # unconditional change probability per valid minute, per bracket
    pooled = absD[nz]
    summary = dict(series=g.series, event=g.event, kind=g.kind, minutes=n, brackets=m,
                   valid_bracket_minutes=int(valid.sum()), changes=int(nz.sum()),
                   brackets_own=int((n_changes >= min_changes).sum()), ladder_days=n / 1440.0,
                   q_pooled=thresholds(pooled).tolist() if pooled.size >= min_changes else None)
    for p in PCTS:
        summary["events_%g" % p] = 0
    if pooled.size < min_changes:
        summary["skipped"] = "fewer than %d changes" % min_changes
        return summary, pd.DataFrame()
    q = np.full((m, len(PCTS)), np.nan)
    fallback = np.zeros(m, dtype=bool)
    qp = thresholds(pooled)
    for j in range(m):
        a = absD[nz[:, j], j]
        if a.size >= min_changes:
            q[j] = thresholds(a)
        else:
            q[j] = qp; fallback[j] = True
    ev_mask = nz & (absD >= q[None, :, 0])
    T, I = np.nonzero(ev_mask)
    if T.size == 0:
        return summary, pd.DataFrame()
    d = D[T, I]; ad = absD[T, I]
    band = np.full(T.shape, PCTS[0])
    for c, p in enumerate(PCTS[1:], start=1):
        band[ad >= q[I, c]] = p
    for p in PCTS:
        summary["events_%g" % p] = int((ad >= q[I, list(PCTS).index(p)]).sum())
    # subsample the 90-95 band
    low = band == PCTS[0]
    keep = ~low | (rng.random(T.shape) < 1.0 / sub)
    weight = np.where(low, float(sub), 1.0)
    T, I, d, ad, band, weight = T[keep], I[keep], d[keep], ad[keep], band[keep], weight[keep]
    rows = dict(series=g.series, event=g.event, kind=g.kind, brackets=m, i=I, strike=g.strikes[I], pos=I / max(m - 1, 1),
                ts=g.ts[T], d=d, absd=ad, band=band, weight=weight, ratio=ad / q[I, 0],
                q90=q[I, 0], q95=q[I, 1], q99=q[I, 2], q999=q[I, 3], n_changes=n_changes[I], fallback=fallback[I],
                spread0=sp[T - 1, I], spread1=sp[T, I], mid0=mid[T - 1, I], vol=g.vol[T, I], oi=np.nan_to_num(g.oi[T, I]),
                hour=((g.ts[T] // 3600) % 24).astype(np.int8))
    base_i = mid[T - 1, I]
    for h in RET_H:
        th = T + h; ok = th < n
        r = np.full(T.shape, np.nan, dtype=np.float32)
        r[ok] = (mid[th[ok], I[ok]] - base_i[ok]) / d[ok]
        rows["ret_%d" % h] = r
    for k in [kk for s in (1, -1) for kk in (s * np.arange(1, K + 1))]:
        J = I + k
        inr = (J >= 0) & (J < m)
        Jc = np.clip(J, 0, m - 1)
        nb_ok = inr & valid[T - 1, Jc]
        base = np.where(nb_ok, mid[T - 1, Jc], np.nan)
        rows["nbsp_%+d" % k] = np.where(nb_ok, sp[T - 1, Jc], np.nan)
        rows["nbrate_%+d" % k] = np.where(nb_ok, rate[Jc], np.nan)
        for h in HORIZONS:
            th = T + h; ok = nb_ok & (th < n)
            r = np.full(T.shape, np.nan, dtype=np.float32)
            r[ok] = (mid[th[ok], Jc[ok]] - base[ok]) / d[ok]
            rows["resp_%+d_%d" % (k, h)] = r
        first = np.full(T.shape, NONE, dtype=np.int16)
        first[~nb_ok] = -1
        found = ~nb_ok
        for h in range(0, FIRST_MAX + 1):
            th = T + h; ok = nb_ok & ~found & (th < n)
            moved = ok.copy()
            moved[ok] = np.abs(mid[th[ok], Jc[ok]] - base[ok]) >= 0.5
            first[moved] = h; found |= moved
        rows["first_%+d" % k] = first
    df = pd.DataFrame(rows)
    return summary, df
