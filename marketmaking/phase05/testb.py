"""Test B — who converges to whom (PROTOCOL §1B). Runs only if Test A passes.

§1B: "For each disagreement, track the following 5, 30 and 60 minutes: did the
deviating bracket move back toward the fit (laggard — the quote was stale and we
were early), or did the rest of the ladder move toward the deviating bracket
(leader — the bracket knew something first and we would have been run over)?"

  "Pass: laggard share above 50% with the 95% confidence interval excluding 50%,
   in at least the non-leader subset (deviations where the bracket was not first
   to move)."

Underlying control, §1B: "For the two WTI series ... align events against the CL
futures path at one-minute resolution where the data exists and report the
laggard share both raw and residual to the underlying's move over the same
horizon. A 'wave' fully explained by the underlying is a trend, not a
propagation."
"""
from __future__ import annotations

import numpy as np

HORIZONS = (5, 30, 60)


def classify(mid_t: float, mid_th: float, fit: float, tol: float = 0.0) -> str:
    """Did the deviating bracket move toward the fit over the horizon?

    "laggard"  - the bracket's mid moved toward the fit's fair value
    "leader"   - the bracket's mid moved further away from the fit
    "flat"     - no move beyond `tol` (excluded from the share, counted)

    Distances are in probability units. `tol` exists because a dead book should
    not be scored as evidence either way; it defaults to 0 so the caller must
    opt in to a dead band.
    """
    if any(np.isnan([mid_t, mid_th, fit])):
        return "missing"
    before = abs(fit - mid_t)
    after = abs(fit - mid_th)
    if abs(after - before) <= tol:
        return "flat"
    return "laggard" if after < before else "leader"


def classify_residual(mid_t, mid_th, fit, und_t, und_th, beta: float = 1.0,
                      tol: float = 0.0) -> str:
    """Laggard/leader after removing the underlying's own move over the horizon.

    The bracket's realised move is reduced by `beta` times the underlying's move
    over the same window, and the residual move is what gets scored. §1B
    requires this for the two WTI series against the CL one-minute path: a
    convergence fully explained by oil moving is a trend, not the quote catching
    up to our fit.

    `beta` is the bracket's sensitivity to the underlying. It is an ESTIMATE and
    must be reported as such; with beta=1 in probability-per-underlying-unit the
    control is only as good as that assumption.
    """
    if any(np.isnan([mid_t, mid_th, fit, und_t, und_th])):
        return "missing"
    realised = mid_th - mid_t
    explained = beta * (und_th - und_t)
    residual_mid = mid_t + (realised - explained)
    return classify(mid_t, residual_mid, fit, tol)


def laggard_share(labels):
    """Share of laggards among decided (laggard|leader) observations, plus counts.

    "flat" and "missing" are excluded from the denominator and reported
    separately, so the share is never silently inflated by dead books.
    """
    labels = list(labels)
    n_lag = sum(1 for x in labels if x == "laggard")
    n_lead = sum(1 for x in labels if x == "leader")
    decided = n_lag + n_lead
    return dict(
        laggard=n_lag, leader=n_lead, decided=decided,
        flat=sum(1 for x in labels if x == "flat"),
        missing=sum(1 for x in labels if x == "missing"),
        share=(n_lag / decided) if decided else float("nan"),
    )
