"""The one number for section 5: how often the ladder's own coherent fair value
sits inside a bracket's quoted spread, so a maker quoting the curve could have
improved on the posted market.

Fair value = the monotone (non-increasing in the strike) least-squares fit to
the mids of the two-sided, tight (spread <= spread_cap) brackets of the ladder
at that minute (pool-adjacent-violators). This is the ladder's OWN shape, not an
external model: it only says what a quoter who insists on monotonicity would
have shown. Sampled every `every` minutes.

Per bracket-minute:
  inside      - bid < fair < ask strictly
  improvable  - fair - bid >= 2 (a bid at bid+1 is still a cent below fair) or
                ask - fair >= 2, i.e. a maker could post inside the spread on
                the side where the market is away from fair, one tick better
                than the book, and still be on the right side of fair by >= 1c
  room        - max(fair - bid, ask - fair) - 1 (the improvement available, cents)
"""
import numpy as np

ROOM_HIST = 20


def pava_decreasing(y, w=None):
    """Non-increasing isotonic regression (weighted least squares)."""
    y = np.asarray(y, dtype=float)
    w = np.ones_like(y) if w is None else np.asarray(w, dtype=float)
    vals, wts, cnt = [], [], []
    for yi, wi in zip(y, w):
        vals.append(yi); wts.append(wi); cnt.append(1)
        while len(vals) > 1 and vals[-2] < vals[-1]:
            v = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / (wts[-2] + wts[-1])
            wts[-2] += wts[-1]; cnt[-2] += cnt[-1]
            vals[-2] = v
            vals.pop(); wts.pop(); cnt.pop()
    return np.repeat(vals, cnt)


def maker_stats(g, every=10, spread_cap=20.0, min_quoted=3):
    acc = dict(minutes=0, nonmono_minutes=0, bracket_minutes=0, inside=0, improvable=0, improvable_bid=0,
               improvable_ask=0, room_sum=0.0, room_hist=[0] * (ROOM_HIST + 1), spread_sum=0.0,
               tight_fraction_sum=0.0)
    if g.kind != "cumul":
        return acc
    mid, bid, ask, sp = g.mid, g.bid, g.ask, g.spread
    n = mid.shape[0]
    for t in range(0, n, every):
        q = ~np.isnan(mid[t]) & (sp[t] <= spread_cap)
        if q.sum() < min_quoted:
            continue
        y = mid[t, q].astype(float)
        fit = pava_decreasing(y)
        b, a = bid[t, q].astype(float), ask[t, q].astype(float)
        acc["minutes"] += 1
        acc["nonmono_minutes"] += int(np.any(np.abs(fit - y) > 1e-6))
        acc["bracket_minutes"] += int(q.sum())
        acc["inside"] += int(((fit > b) & (fit < a)).sum())
        ib = (fit - b) >= 2.0
        ia = (a - fit) >= 2.0
        acc["improvable_bid"] += int(ib.sum()); acc["improvable_ask"] += int(ia.sum()); acc["improvable"] += int((ib | ia).sum())
        room = np.clip(np.maximum(fit - b, a - fit) - 1.0, 0, None)
        acc["room_sum"] += float(room.sum())
        h = np.bincount(np.clip(np.floor(room), 0, ROOM_HIST).astype(int), minlength=ROOM_HIST + 1)
        acc["room_hist"] = [x + int(y_) for x, y_ in zip(acc["room_hist"], h)]
        acc["spread_sum"] += float((a - b).sum())
    return acc


def merge(acc, other):
    for k, v in other.items():
        if isinstance(v, list):
            acc[k] = [x + y for x, y in zip(acc.get(k, [0] * len(v)), v)]
        else:
            acc[k] = acc.get(k, 0) + v
    return acc
