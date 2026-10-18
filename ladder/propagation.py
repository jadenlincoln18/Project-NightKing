"""Propagation / impulse response on cumulative ladders (brief section 2.2).

A "move" is a change of a bracket's mid of at least `thr` cents between one
minute and the next, with that bracket two-sided and its spread <= spread_cap
on both minutes (so the mid means something). For each move of bracket i at
minute t and each neighbour i+k (k = +-1..3), also two-sided and tight at t-1:

  response(h) = (mid[t+h, i+k] - mid[t-1, i+k]) / (mid[t, i] - mid[t-1, i])

the neighbour's cumulative move from before the impulse to h minutes after,
in units of the impulse. On a P(>X) ladder a shift of the underlying moves
every bracket the same way, so response ~ 1 is "repriced with it", ~ 0 is
"did not respond", and sign agreement is the direction predictability.

h = 0 is the same minute. "Stale" neighbours are those unchanged at t
(|D| = 0); for them the executable trade is also scored: if the impulse was up,
buy the neighbour at its ask at t and sell at its bid at t+h (down: the
reverse), net of taker fees on both legs. Positive means the lag was tradeable.

Accumulators are sums, so events aggregate by addition.
"""
import numpy as np

from .fees import fee_cents

HORIZONS = (0, 1, 2, 5, 10, 30)
KS = (-3, -2, -1, 1, 2, 3)
BANDS = ("body", "tail")


def _band(mid):
    return np.where((mid < 10) | (mid > 90), "tail", "body")


def fee_v(p):
    p = np.clip(p / 100.0, 0.0, 1.0)
    return 0.07 * p * (1.0 - p) * 100.0


def impulse(g, thr=2.0, spread_cap=10.0, horizons=HORIZONS, sample=400, rng=None):
    """Returns (acc, samples). acc[(k, h, init_band, nb_band, stale)] = [n, sum_resp, n_same_sign,
    n_resp_known, n_pnl, sum_pnl, n_pnl_pos, sum_pnl_pos_only]; acc[('init', band)] = n moves;
    acc[('co', k, band)] = [n, n_moved_same_minute]. samples: list of (k, h, pnl) for stale trades."""
    rng = rng or np.random.default_rng(0)
    mid, bid, ask, sp = g.mid, g.bid, g.ask, g.spread
    n, m = mid.shape
    valid = ~np.isnan(mid) & (sp <= spread_cap)
    D = np.full((n, m), np.nan, dtype=np.float32)
    D[1:] = mid[1:] - mid[:-1]
    D[~(valid & np.roll(valid, 1, axis=0))] = np.nan
    D[0] = np.nan
    init = np.abs(np.nan_to_num(D)) >= thr
    acc = {}
    samples = []
    T, I = np.nonzero(init)
    if T.size == 0:
        return acc, samples
    imp = D[T, I]
    iband = _band(mid[T - 1, I])
    for b in BANDS:
        acc[("init", b)] = int((iband == b).sum())
    for k in KS:
        J = I + k
        ok = (J >= 0) & (J < m)
        t, i, j, d, ib = T[ok], I[ok], J[ok], imp[ok], iband[ok]
        ok2 = valid[t - 1, j]
        t, i, j, d, ib = t[ok2], i[ok2], j[ok2], d[ok2], ib[ok2]
        if t.size == 0:
            continue
        nb = _band(mid[t - 1, j])
        dj = D[t, j]
        moved_same = np.abs(np.nan_to_num(dj)) >= 1.0
        stale = np.nan_to_num(dj, nan=1.0) == 0.0
        for b in BANDS:
            sel = ib == b
            acc[("co", k, b)] = [int(sel.sum()), int((moved_same & sel).sum())]
        base = mid[t - 1, j]
        for h in horizons:
            th = t + h
            inb = th < n
            resp = np.full(t.shape, np.nan, dtype=np.float64)
            resp[inb] = (mid[th[inb], j[inb]] - base[inb]) / d[inb]
            known = ~np.isnan(resp)
            same = known & (resp > 0)
            # stale-neighbour trade
            pnl = np.full(t.shape, np.nan, dtype=np.float64)
            up = d > 0
            s_in = stale & inb
            a0 = ask[t, j]; b0 = bid[t, j]
            ah = np.full(t.shape, np.nan, dtype=np.float32); bh = np.full(t.shape, np.nan, dtype=np.float32)
            ah[inb] = ask[th[inb], j[inb]]; bh[inb] = bid[th[inb], j[inb]]
            pnl_up = bh - a0 - fee_v(np.nan_to_num(a0)) - fee_v(np.nan_to_num(bh))
            pnl_dn = b0 - ah - fee_v(np.nan_to_num(b0)) - fee_v(np.nan_to_num(ah))
            pnl[s_in & up] = pnl_up[s_in & up]
            pnl[s_in & ~up] = pnl_dn[s_in & ~up]
            pk = ~np.isnan(pnl)
            for ib_ in BANDS:
                for nb_ in BANDS:
                    for st in (False, True):
                        sel = (ib == ib_) & (nb == nb_) & (stale == st)
                        if not sel.any():
                            continue
                        key = (k, h, ib_, nb_, st)
                        kk = known & sel
                        pp = pk & sel
                        a = acc.setdefault(key, [0, 0.0, 0, 0, 0, 0.0, 0, 0.0])
                        a[0] += int(sel.sum()); a[1] += float(resp[kk].sum()); a[2] += int((same & sel).sum()); a[3] += int(kk.sum())
                        a[4] += int(pp.sum()); a[5] += float(pnl[pp].sum()); a[6] += int((pnl[pp] > 0).sum()); a[7] += float(np.clip(pnl[pp], 0, None).sum())
            if abs(k) == 1 and pk.any():
                idx = np.flatnonzero(pk)
                if idx.size > sample:
                    idx = rng.choice(idx, sample, replace=False)
                samples.extend((k, h, float(pnl[x]), str(ib[x]), str(nb[x])) for x in idx)
    return acc, samples


def merge(acc, other):
    for key, v in other.items():
        if key[0] == "init":
            acc[key] = acc.get(key, 0) + v
        else:
            a = acc.setdefault(key, [0] * len(v))
            for q in range(len(v)):
                a[q] += v[q]
    return acc
