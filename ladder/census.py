"""Violation census on one ladder's minute grid (brief section 2.1 and 2.3).

Executable prices only: a violation on a cumulative ladder is
    edge = bid(X_j) - ask(X_i) > 0   for strikes X_i < X_j
i.e. you can buy the lower threshold for less than you can sell the higher one.
Buying YES on X_i at its ask and selling YES on X_j at its bid pays
X_i < settle <= X_j: +1, otherwise 0, so a positive edge is a locked profit.
The edge is computed from the bid and ask directly, so the spread is already
crossed; the only friction left is the taker fee on each leg:
    net = edge - fee(ask_i) - fee(bid_j)

Three views, all reported:
  close   - carried-forward candle closes: the top of book as it stood at the end
            of each minute. The conservative, "it was there" view.
  any     - the best pair j > i for each i (not only the adjacent one).
  intra   - bid_high(X_j) - ask_low(X_i) within the same minute, only where both
            brackets printed a candle that minute. An UPPER bound on sub-minute
            crossings: the two extremes need not have coexisted.
  mid     - mid(X_j) > mid(X_i) with both spreads <= spread_cap. Not executable;
            the "shape" view used for propagation and the maker question.

Range ladders have no two-leg shape constraint (a bracket price is itself a
non-negative density value); their constraint is the sum, reported as the ask
sum against 100 plus fees (buy every bracket) and the bid sum (sell every
bracket), all legs crossed.
"""
import numpy as np
import pandas as pd

from .fees import fee_cents, TAKER

THRESHOLDS = (1.0, 2.0, 3.0, 5.0)
SPREAD_CAP = 10.0
HIST_MAX = 50  # cents


def runs_1d(mask):
    """Start indices and lengths of True runs in a 1-D bool array."""
    if mask.size == 0:
        return np.zeros(0, int), np.zeros(0, int)
    m = np.concatenate(([0], mask.astype(np.int8), [0]))
    idx = np.flatnonzero(np.diff(m))
    return idx[0::2], idx[1::2] - idx[0::2]


def trailing_sum(x, w):
    c = np.cumsum(np.nan_to_num(x), axis=0)
    out = c.copy()
    out[w:] = c[w:] - c[:-w]
    return out


def nan_rev_cummax(b):
    f = np.where(np.isnan(b), -np.inf, b)
    r = np.maximum.accumulate(f[:, ::-1], axis=1)[:, ::-1]
    r[np.isinf(r)] = np.nan
    return r


def fee_vec(p, coef=TAKER):
    p = np.clip(p / 100.0, 0.0, 1.0)
    return coef * p * (1.0 - p) * 100.0


def hist_counts(x, lo=1, hi=HIST_MAX):
    x = x[~np.isnan(x)]
    x = np.clip(np.floor(x), lo, hi).astype(int)
    return np.bincount(x - lo, minlength=hi - lo + 1).tolist()


def band(mid):
    """Moneyness band from a mid in cents."""
    return np.where(np.isnan(mid), "na", np.where((mid < 10) | (mid > 90), "tail", "body"))


def cumul_census(g, spread_cap=SPREAD_CAP):
    bid, ask, mid, sp = g.bid, g.ask, g.mid, g.spread
    n, m = bid.shape
    edge = bid[:, 1:] - ask[:, :-1]
    pair_q = ~np.isnan(edge)
    best = nan_rev_cummax(bid)[:, 1:] - ask[:, :-1]
    intra = g.bid_hi[:, 1:] - g.ask_lo[:, :-1]
    intra_q = ~np.isnan(intra)
    tight = sp <= spread_cap
    mid_edge = mid[:, 1:] - mid[:, :-1]
    mid_q = tight[:, 1:] & tight[:, :-1] & ~np.isnan(mid_edge)
    both_q = ~np.isnan(bid) & ~np.isnan(ask)
    s = dict(series=g.series, event=g.event, kind=g.kind, minutes=n, brackets=m, candles=g.n_candles,
             quoted_bracket_minutes=int(both_q.sum()), tight_bracket_minutes=int((both_q & tight).sum()),
             pair_minutes=int(pair_q.sum()), intra_pair_minutes=int(intra_q.sum()), mid_pair_minutes=int(mid_q.sum()),
             mid_viol_minutes=int((mid_q & (mid_edge > 0)).sum()),
             mid_viol_minutes_2c=int((mid_q & (mid_edge >= 2)).sum()),
             spread_median=float(np.nanmedian(sp)) if both_q.any() else np.nan,
             hist_close=hist_counts(edge), hist_any=hist_counts(best), hist_intra=hist_counts(intra))
    ladder_q = pair_q.any(axis=1)
    s["ladder_minutes"] = int(ladder_q.sum())  # minutes with at least one quoted adjacent pair
    s["ladder_minutes_intra"] = int(intra_q.any(axis=1).sum())
    for thr in THRESHOLDS:
        k = "%dc" % int(thr)
        s["viol_close_" + k] = int(np.nansum(edge >= thr))
        s["viol_any_" + k] = int(np.nansum(best >= thr))
        s["viol_intra_" + k] = int(np.nansum(intra >= thr))
        s["ladder_viol_" + k] = int((np.nan_to_num(edge, nan=-1.0) >= thr).any(axis=1).sum())  # ladder-minutes with any violating pair
        s["ladder_intra_" + k] = int((np.nan_to_num(intra, nan=-1.0) >= thr).any(axis=1).sum())
    # episodes on the adjacent, close-based edge at >= 1c
    vol60 = trailing_sum(g.vol, 60)
    vol_td = np.cumsum(g.vol, axis=0)
    eps = []
    for p in range(m - 1):
        col = edge[:, p]
        mask = np.nan_to_num(col, nan=-1.0) >= 1.0
        starts, lens = runs_1d(mask)
        for st, L in zip(starts, lens):
            en = st + L
            seg = col[st:en]
            a0, b0 = float(ask[st, p]), float(bid[st, p + 1])
            fee = fee_cents(a0) + fee_cents(b0)
            k = min(en, n - 1)
            eps.append(dict(
                series=g.series, event=g.event, kind=g.kind, pair=p, strike_i=float(g.strikes[p]), strike_j=float(g.strikes[p + 1]),
                ts=int(g.ts[st]), duration_min=int(L), ended=bool(en < n),
                edge_start=float(seg[0]), edge_max=float(np.nanmax(seg)), edge_mean=float(np.nanmean(seg)),
                ask_i=a0, bid_j=b0, fee=float(fee), net_start=float(seg[0] - fee), net_max=float(np.nanmax(seg) - fee),
                spread_i=float(sp[st, p]), spread_j=float(sp[st, p + 1]),
                mid_i=float(mid[st, p]), mid_j=float(mid[st, p + 1]),
                fresh_i=bool(g.has[st, p]), fresh_j=bool(g.has[st, p + 1]),
                end_fresh_i=bool(g.has[k, p]) if en < n else False, end_fresh_j=bool(g.has[k, p + 1]) if en < n else False,
                vol60_i=float(vol60[st, p]), vol60_j=float(vol60[st, p + 1]),
                vol_td_i=float(vol_td[st, p]), vol_td_j=float(vol_td[st, p + 1]),
                oi_i=float(np.nan_to_num(g.oi[st, p])), oi_j=float(np.nan_to_num(g.oi[st, p + 1])),
                vol_in_i=float(g.vol[st:en, p].sum()), vol_in_j=float(g.vol[st:en, p + 1].sum())))
    s["episodes"] = len(eps)
    return s, pd.DataFrame(eps)


def range_census(g):
    bid, ask = g.bid, g.ask
    n, m = bid.shape
    all_a = ~np.isnan(ask).any(axis=1)
    all_b = ~np.isnan(bid).any(axis=1)
    s_ask = np.where(all_a, np.nansum(ask, axis=1), np.nan)
    s_bid = np.where(all_b, np.nansum(bid, axis=1), np.nan)
    fee_a = np.where(all_a, np.nansum(fee_vec(np.nan_to_num(ask)), axis=1), np.nan)
    fee_b = np.where(all_b, np.nansum(fee_vec(np.nan_to_num(bid)), axis=1), np.nan)
    buy = 100.0 - s_ask - fee_a
    sell = s_bid - 100.0 - fee_b
    gross_a = s_ask - 100.0
    gross_b = 100.0 - s_bid
    sp = g.spread
    s = dict(series=g.series, event=g.event, kind=g.kind, minutes=n, brackets=m, candles=g.n_candles,
             quoted_bracket_minutes=int((~np.isnan(bid) & ~np.isnan(ask)).sum()),
             all_ask_minutes=int(all_a.sum()), all_bid_minutes=int(all_b.sum()),
             ask_excess_median=float(np.nanmedian(gross_a)) if all_a.any() else np.nan,
             ask_excess_p10=float(np.nanpercentile(gross_a, 10)) if all_a.any() else np.nan,
             bid_short_median=float(np.nanmedian(gross_b)) if all_b.any() else np.nan,
             bid_short_p10=float(np.nanpercentile(gross_b, 10)) if all_b.any() else np.nan,
             spread_sum_median=float(np.nanmedian(np.where(all_a & all_b, np.nansum(sp, axis=1), np.nan))) if (all_a & all_b).any() else np.nan,
             buy_all_minutes=int(np.nansum(buy > 0)), sell_all_minutes=int(np.nansum(sell > 0)),
             buy_all_gross_minutes=int(np.nansum(gross_a < 0)), sell_all_gross_minutes=int(np.nansum(gross_b < 0)),
             hist_ask_excess=hist_counts(np.clip(gross_a, 0, None) + 1), hist_bid_short=hist_counts(np.clip(gross_b, 0, None) + 1))
    eps = []
    for name, x, gross in (("buy_all", buy, gross_a), ("sell_all", sell, gross_b)):
        starts, lens = runs_1d(np.nan_to_num(x, nan=-1.0) > 0)
        for st, L in zip(starts, lens):
            eps.append(dict(series=g.series, event=g.event, kind=g.kind, side=name, ts=int(g.ts[st]), duration_min=int(L),
                            legs=m, net_start=float(x[st]), net_max=float(np.nanmax(x[st:st + L])),
                            gross_start=float(-gross[st]), ended=bool(st + L < n)))
    s["episodes"] = len(eps)
    return s, pd.DataFrame(eps)


def census(g):
    return cumul_census(g) if g.kind == "cumul" else range_census(g)
