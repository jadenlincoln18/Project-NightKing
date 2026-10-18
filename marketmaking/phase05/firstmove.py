"""The §1B "first to move" rule, adopted from `waves/` (read, never modified).

§1B fixes this before looking, and the conventions are transcribed from
`waves/census.py` and `waves/FINDINGS_WAVES.md` §"Per-bracket normalisation":

  - "A move is a non-zero minute-to-minute change in a bracket's mid on the
     one-minute grid, on tight two-sided brackets only."
  - "An event is a move at or above the 95th percentile of that bracket's own
     absolute non-zero changes. A bracket with fewer than 50 non-zero changes
     borrows its ladder's pooled distribution and is flagged; a ladder with
     fewer than 50 changes in total is skipped."
  - "Mids move in half-cent steps, so these thresholds are discrete and ties
     are common — 'at or above the p95 value' takes materially more than 5% of
     changes, and the band is labelled by the percentile cleared, not by an
     assumed share."
  - "The deviating bracket is first to move in a preceding window of W = 15
     minutes if it recorded an event in that window and no other bracket in the
     same ladder recorded an event at a strictly earlier minute within it. Ties
     at the same minute resolve to not first."

Conventions inherited from `waves/census.py` rather than reinvented:
  - validity = mid present AND spread <= `spread_cap` (default 10.0 cents) on
    the minute and the one before, so the change means something;
  - "non-zero" = |change| >= 0.5 cents, because mids move in half-cent steps.

WINDOW CONVENTION, flagged as an assumption: §1B says "a preceding window of
W = 15 minutes" without fixing the endpoints. This module uses the inclusive
window [t - W, t]. The alternative [t - W + 1, t] differs by one minute. The
choice is exposed as `W` and documented in FINDINGS_PHASE05.md as an assumption
rather than a measurement.
"""
from __future__ import annotations

import numpy as np

P95 = 95.0
MIN_CHANGES = 50
SPREAD_CAP = 10.0
NONZERO = 0.5  # cents; mids move in half-cent steps
W_DEFAULT = 15


class LadderSkipped(Exception):
    """A ladder with fewer than MIN_CHANGES non-zero changes in total is skipped."""


def mid_changes(mid, spread, spread_cap: float = SPREAD_CAP):
    """Minute-to-minute mid changes on tight two-sided brackets. NaN elsewhere.

    Mirrors `waves.census.census`: a change exists only where the bracket is
    valid on both this minute and the previous one.
    """
    mid = np.asarray(mid, dtype=float)
    spread = np.asarray(spread, dtype=float)
    n, m = mid.shape
    valid = ~np.isnan(mid) & ~np.isnan(spread) & (spread <= spread_cap)
    d = np.full((n, m), np.nan, dtype=float)
    d[1:] = mid[1:] - mid[:-1]
    prev_valid = np.vstack([np.zeros((1, m), dtype=bool), valid[:-1]])
    d[~(valid & prev_valid)] = np.nan
    d[0] = np.nan
    return d


def event_mask(mid, spread, spread_cap: float = SPREAD_CAP,
               min_changes: int = MIN_CHANGES, pct: float = P95):
    """Per-bracket p95 event mask, with the pooled fallback and the ladder skip.

    Returns (mask, info). `info` carries the per-bracket thresholds, the
    fallback flags and the realised share of changes that clear the threshold —
    reported rather than assumed, because the discrete half-cent grid makes the
    realised share materially above 5%.
    """
    d = mid_changes(mid, spread, spread_cap)
    absd = np.abs(d)
    nz = np.nan_to_num(absd) >= NONZERO
    n_changes = nz.sum(axis=0)
    pooled = absd[nz]

    if pooled.size < min_changes:
        raise LadderSkipped(
            "ladder has %d non-zero changes, fewer than the %d §1B requires"
            % (int(pooled.size), min_changes)
        )

    m = mid.shape[1]
    q = np.full(m, np.nan)
    fallback = np.zeros(m, dtype=bool)
    q_pooled = float(np.percentile(pooled, pct))
    for j in range(m):
        a = absd[nz[:, j], j]
        if a.size >= min_changes:
            q[j] = float(np.percentile(a, pct))
        else:
            q[j] = q_pooled
            fallback[j] = True

    mask = nz & (absd >= q[None, :])
    info = dict(
        thresholds=q, fallback=fallback, q_pooled=q_pooled,
        n_changes=n_changes, n_events=int(mask.sum()),
        realised_share=float(mask.sum() / nz.sum()) if nz.sum() else float("nan"),
        percentile_cleared=pct, n_fallback_brackets=int(fallback.sum()),
    )
    return mask, info


def first_to_move(mask, t: int, j: int, W: int = W_DEFAULT):
    """Was bracket `j` first to move in the window [t - W, t]?

    Returns (verdict, detail) where verdict is one of:
      "first"     - j had an event, and no other bracket had one strictly earlier
      "not_first" - another bracket had an event at a strictly earlier minute,
                    OR tied at the same minute (§1B: ties resolve to NOT first)
      "no_event"  - j recorded no event in the window, so the rule does not apply

    Ties resolving to "not_first" is deliberate and load-bearing: simultaneous
    repricing is a batch update by one maker, "precisely the case where there is
    nothing to catch".
    """
    mask = np.asarray(mask, dtype=bool)
    lo = max(0, t - W)
    hi = min(mask.shape[0] - 1, t)
    if hi < lo:
        return "no_event", dict(own_minute=None, other_minute=None)

    win = mask[lo:hi + 1]
    own = np.flatnonzero(win[:, j])
    if own.size == 0:
        return "no_event", dict(own_minute=None, other_minute=None)
    own_minute = int(own[0]) + lo

    others = np.delete(win, j, axis=1)
    other_rows = np.flatnonzero(others.any(axis=1))
    other_minute = int(other_rows[0]) + lo if other_rows.size else None

    if other_minute is None or own_minute < other_minute:
        return "first", dict(own_minute=own_minute, other_minute=other_minute)
    # strictly earlier OR tied -> not first
    return "not_first", dict(own_minute=own_minute, other_minute=other_minute)
